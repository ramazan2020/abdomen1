import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, require_doctor_or_admin
from app.db.models import Annotation, Case, InferenceBatch, InferenceRun, ModelOutput, ModelVersion, User
from app.db.session import get_db
from app.schemas.inference import (
    InferenceBatchResponse,
    RunComparisonRequest,
    RunDefaultRequest,
)
from app.services.inference_service import create_inference_batch

router = APIRouter(prefix="/inference", tags=["inference"])


def _get_case_or_404(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case bulunamadı")
    return case


def _get_batch_or_404(db: Session, batch_id: uuid.UUID) -> InferenceBatch:
    stmt = (
        select(InferenceBatch)
        .options(selectinload(InferenceBatch.runs).selectinload(InferenceRun.model_version))
        .where(InferenceBatch.id == batch_id)
    )
    batch = db.execute(stmt).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch bulunamadı")
    return batch


def _create_batch_and_runs(
    db: Session, *, case: Case, batch_type: str, model_versions: list[ModelVersion], actor: User
) -> InferenceBatch:
    batch = create_inference_batch(db, case=case, batch_type=batch_type, model_versions=model_versions, actor_id=actor.id)
    if batch is None:
        raise HTTPException(
            status_code=422,
            detail=f"'{batch_type}' modunda çalışacak aktif model bulunamadı",
        )
    return batch


@router.post("/run-default", response_model=InferenceBatchResponse, status_code=status.HTTP_201_CREATED)
def run_default(
    payload: RunDefaultRequest, db: Session = Depends(get_db), user: User = Depends(require_doctor_or_admin)
) -> InferenceBatch:
    """Case `ready` olunca otomatik tetiklenir (plan Bölüm 4) — sadece
    `run_mode='default'` ve `status='active'` modeller paralel çalışır."""
    case = _get_case_or_404(db, payload.case_id)
    if case.status != "ready":
        raise HTTPException(status_code=409, detail="Case henüz 'ready' durumunda değil")

    model_versions = list(
        db.execute(
            select(ModelVersion).where(ModelVersion.run_mode == "default", ModelVersion.status == "active")
        ).scalars().all()
    )
    batch = _create_batch_and_runs(db, case=case, batch_type="default", model_versions=model_versions, actor=user)
    return _get_batch_or_404(db, batch.id)


@router.post("/run-comparison", response_model=InferenceBatchResponse, status_code=status.HTTP_201_CREATED)
def run_comparison(
    payload: RunComparisonRequest, db: Session = Depends(get_db), user: User = Depends(require_doctor_or_admin)
) -> InferenceBatch:
    """Sadece doktor/admin'in açık talebiyle tetiklenir ("Diğer modelleri de
    çalıştır" butonu, plan Bölüm 4/5). `model_version_ids` verilmezse
    `run_mode='comparison'` olan tüm aktif modeller çalışır."""
    case = _get_case_or_404(db, payload.case_id)
    if case.status != "ready":
        raise HTTPException(status_code=409, detail="Case henüz 'ready' durumunda değil")

    if payload.model_version_ids:
        model_versions = list(
            db.execute(
                select(ModelVersion).where(
                    ModelVersion.id.in_(payload.model_version_ids), ModelVersion.status == "active"
                )
            ).scalars().all()
        )
    else:
        model_versions = list(
            db.execute(
                select(ModelVersion).where(ModelVersion.run_mode == "comparison", ModelVersion.status == "active")
            ).scalars().all()
        )
    batch = _create_batch_and_runs(db, case=case, batch_type="comparison", model_versions=model_versions, actor=user)
    return _get_batch_or_404(db, batch.id)


@router.get("/batches/{batch_id}", response_model=InferenceBatchResponse)
def get_batch(batch_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> InferenceBatch:
    return _get_batch_or_404(db, batch_id)


@router.post("/batches/{batch_id}/consensus")
def compute_consensus(
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_doctor_or_admin),
) -> dict:
    """Weighted Boxes Fusion — batch'teki tüm bbox tahminlerini ensemble eder.

    Sonuç saklanmaz; çağıran (frontend) kutulara overlay için kullanır.
    Koordinatlar orijinal piksel uzayındadır (512×512 normaliz. varsayımıyla)."""
    batch = _get_batch_or_404(db, batch_id)

    succeeded_mv_ids = [r.model_version_id for r in batch.runs if r.status == "succeeded"]
    if not succeeded_mv_ids:
        raise HTTPException(status_code=422, detail="Başarılı inference run bulunamadı")

    bbox_output_ids = [
        o.id for o in db.execute(
            select(ModelOutput).where(
                ModelOutput.model_version_id.in_(succeeded_mv_ids),
                ModelOutput.output_type == "bbox",
            )
        ).scalars().all()
    ]
    if not bbox_output_ids:
        raise HTTPException(status_code=422, detail="Bu batch'te bbox çıktısı olan model bulunamadı")

    pred_anns = db.execute(
        select(Annotation).where(
            Annotation.case_id == batch.case_id,
            Annotation.source == "prediction",
            Annotation.model_output_id.in_(bbox_output_ids),
            Annotation.geometry_type == "bbox",
            Annotation.status == "active",
        )
    ).scalars().all()

    if not pred_anns:
        raise HTTPException(status_code=422, detail="Bu batch'te bbox tahmini bulunamadı")

    try:
        from ensemble_boxes import weighted_boxes_fusion
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"ensemble-boxes kütüphanesi kurulu değil: {exc}")

    NORM = 512.0
    by_image: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for a in pred_anns:
        geo = a.geometry or {}
        oid = str(a.model_output_id)
        by_image[a.image_id][oid].append({
            "box": [
                geo.get("x1", 0) / NORM, geo.get("y1", 0) / NORM,
                geo.get("x2", 0) / NORM, geo.get("y2", 0) / NORM,
            ],
            "score": float(a.confidence) if a.confidence is not None else 0.5,
            "label": float(a.class_id),
        })

    consensus_boxes: list[dict] = []
    model_count = len({str(a.model_output_id) for a in pred_anns})

    for image_id, by_output in sorted(by_image.items()):
        boxes_list, scores_list, labels_list = [], [], []
        for out_anns in by_output.values():
            boxes_list.append([d["box"] for d in out_anns])
            scores_list.append([d["score"] for d in out_anns])
            labels_list.append([d["label"] for d in out_anns])

        try:
            wbf_boxes, wbf_scores, wbf_labels = weighted_boxes_fusion(
                boxes_list, scores_list, labels_list, iou_thr=0.55, skip_box_thr=0.0001
            )
        except Exception:
            continue

        for box, score, label in zip(wbf_boxes, wbf_scores, wbf_labels):
            consensus_boxes.append({
                "image_id": image_id,
                "class": int(label),
                "x1": float(box[0] * NORM), "y1": float(box[1] * NORM),
                "x2": float(box[2] * NORM), "y2": float(box[3] * NORM),
                "score": float(score),
            })

    return {
        "batch_id": str(batch.id),
        "case_id": str(batch.case_id),
        "model_count": model_count,
        "input_box_count": len(pred_anns),
        "consensus_box_count": len(consensus_boxes),
        "consensus_boxes": consensus_boxes,
    }


@router.get("/cases/{case_id}/batches", response_model=list[InferenceBatchResponse])
def list_case_batches(case_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(get_current_user)) -> list[InferenceBatch]:
    _get_case_or_404(db, case_id)
    stmt = (
        select(InferenceBatch)
        .options(selectinload(InferenceBatch.runs).selectinload(InferenceRun.model_version))
        .where(InferenceBatch.case_id == case_id)
        .order_by(InferenceBatch.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())
