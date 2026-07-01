import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user, require_doctor_or_admin
from app.db.models import Case, InferenceBatch, InferenceRun, ModelVersion, User
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
