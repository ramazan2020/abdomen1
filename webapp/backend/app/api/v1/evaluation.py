"""Model karşılaştırma ve değerlendirme API (plan Bölüm 7, Faz 6).

Endpoint'ler:
  GET  /evaluation/models   — tahmin verisi olan aktif model listesi
  POST /evaluation/compare  — snapshot GT vs model tahminleri (src.evaluation.Evaluator)
"""
from __future__ import annotations

import uuid

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin
from app.db.models import Annotation, DatasetSnapshot, ModelOutput, ModelVersion, User
from app.services.dataset_export_service import load_manifest

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

SUPER_CLASS_NAMES = [
    "acute_cholecystitis",
    "kidney_ureter_stone",
    "acute_pancreatitis",
    "aortic_aneurysm_dissection",
    "acute_appendicitis",
    "acute_diverticulitis",
]


class CompareRequest(BaseModel):
    snapshot_id: str
    model_ids: list[str] | None = None  # None → tüm aktif modeller
    iou_threshold: float = 0.3


@router.get("/models")
def list_models(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[dict]:
    """Aktif model versiyonlarını bbox output sayısıyla listeler."""
    mvs = db.execute(
        select(ModelVersion).where(ModelVersion.status == "active")
    ).scalars().all()
    result = []
    for mv in mvs:
        bbox_output_ids = [o.id for o in (mv.outputs or []) if o.output_type == "bbox"]
        pred_count_val = 0
        if bbox_output_ids:
            pred_count_val = db.scalar(
                select(func.count(Annotation.id)).where(
                    Annotation.source == "prediction",
                    Annotation.geometry_type == "bbox",
                    Annotation.status == "active",
                    Annotation.model_output_id.in_(bbox_output_ids),
                )
            ) or 0
        result.append({
            "id": str(mv.id),
            "name": mv.name,
            "architecture": mv.architecture,
            "run_mode": mv.run_mode,
            "prediction_count": pred_count_val,
        })
    return result


@router.post("/compare")
def compare_models(
    body: CompareRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> dict:
    """Snapshot GT üzerinde model tahminlerini karşılaştırır (src.evaluation.Evaluator)."""
    snap = db.get(DatasetSnapshot, uuid.UUID(body.snapshot_id))
    if snap is None:
        raise HTTPException(status_code=404, detail="Snapshot bulunamadı")
    if not snap.manifest_storage_key:
        raise HTTPException(status_code=422, detail="Snapshot manifest'i bulunamadı")

    # ── GT DataFrame ────────────────────────────────────────────────────────
    manifest = load_manifest(snap.manifest_storage_key)
    gt_rows: list[dict] = []
    snap_case_ids: set[str] = set()
    case_label_map: dict[str, str] = {}

    for case_data in manifest.get("cases", []):
        cid = case_data["case_id"]
        clabel = case_data.get("case_label", cid)
        snap_case_ids.add(cid)
        case_label_map[cid] = clabel
        for s in case_data.get("slices", []):
            for ann in s.get("annotations", []):
                if ann.get("geometry_type") != "bbox":
                    continue
                geo = ann.get("geometry", {})
                gt_rows.append({
                    "case": clabel,
                    "image_id": s["image_id"],
                    "class": ann["class_id"],
                    "x1": geo.get("x1", 0), "y1": geo.get("y1", 0),
                    "x2": geo.get("x2", 0), "y2": geo.get("y2", 0),
                })

    if not gt_rows:
        raise HTTPException(status_code=422, detail="Snapshot'ta bbox GT annotasyonu bulunamadı")

    gt_df = pd.DataFrame(gt_rows)
    snap_case_uuids = [uuid.UUID(cid) for cid in snap_case_ids]

    # ── Model listesi ────────────────────────────────────────────────────────
    if body.model_ids:
        model_uuids = [uuid.UUID(mid) for mid in body.model_ids]
        mvs = db.execute(
            select(ModelVersion).where(ModelVersion.id.in_(model_uuids))
        ).scalars().all()
    else:
        mvs = db.execute(
            select(ModelVersion).where(ModelVersion.status == "active")
        ).scalars().all()

    # ── Pred DataFrame (model başına) ────────────────────────────────────────
    models_pred: dict[str, pd.DataFrame] = {}
    for mv in mvs:
        bbox_output_ids = [
            o.id for o in db.execute(
                select(ModelOutput).where(
                    ModelOutput.model_version_id == mv.id,
                    ModelOutput.output_type == "bbox",
                )
            ).scalars().all()
        ]
        if not bbox_output_ids:
            continue

        pred_anns = db.execute(
            select(Annotation).where(
                Annotation.case_id.in_(snap_case_uuids),
                Annotation.source == "prediction",
                Annotation.model_output_id.in_(bbox_output_ids),
                Annotation.geometry_type == "bbox",
                Annotation.status == "active",
            )
        ).scalars().all()

        if not pred_anns:
            continue

        pred_rows = []
        for a in pred_anns:
            geo = a.geometry or {}
            pred_rows.append({
                "case": case_label_map.get(str(a.case_id), str(a.case_id)),
                "image_id": a.image_id,
                "class": a.class_id,
                "x1": geo.get("x1", 0), "y1": geo.get("y1", 0),
                "x2": geo.get("x2", 0), "y2": geo.get("y2", 0),
                "score": float(a.confidence) if a.confidence is not None else 0.5,
            })
        models_pred[mv.name] = pd.DataFrame(pred_rows)

    if not models_pred:
        raise HTTPException(
            status_code=422,
            detail="Karşılaştırılacak model tahmini bulunamadı. "
                   "Bu snapshot'un case'lerinde önce inference çalıştırın.",
        )

    # ── Evaluator ─────────────────────────────────────────────────────────────
    try:
        from src.evaluation import Evaluator
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=f"Evaluator modülü yüklenemedi: {exc}")

    ev = Evaluator(gt_df)
    comparison_df = ev.compare(models_pred)

    detailed: dict[str, dict] = {}
    for model_name, pred_df in models_pred.items():
        try:
            f1 = ev.f1_at_iou(pred_df, iou_th=body.iou_threshold)
            per_class_named = {}
            for cls_id, metrics in f1["per_class"].items():
                name = SUPER_CLASS_NAMES[int(cls_id)] if int(cls_id) < len(SUPER_CLASS_NAMES) else str(cls_id)
                per_class_named[name] = {k: round(float(v), 4) for k, v in metrics.items()}
            detailed[model_name] = {
                "per_class": per_class_named,
                "macro_f1": round(f1["macro_f1"], 4),
                "micro_f1": round(f1["micro_f1"], 4),
            }
        except Exception as exc:
            detailed[model_name] = {"error": str(exc)}

    return {
        "snapshot_name": snap.snapshot_name,
        "gt_case_count": len(snap_case_ids),
        "gt_annotation_count": len(gt_rows),
        "iou_threshold": body.iou_threshold,
        "comparison": comparison_df.to_dict("records"),
        "detailed": detailed,
    }
