"""Mimari-bazlı inference sarmalayıcıları (plan Bölüm 4 tablosu).

Faz 2 kapsamı: sadece YOLO det "hazır" (src.detection.predict_volume doğrudan
kullanılabilir). Diğer mimariler (RF-DETR/D-FINE, nnU-Net, OrganBagTransformer,
sınıflandırma) Faz 5'te eklenecek — şimdilik MLDependencyUnavailable fırlatır,
job 'failed' olur, sunucu/worker çökmez (plan Bölüm 1 tasarım ilkesi).
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Annotation, AnnotationGroup, Case, InferenceBatch, InferenceRun,
    ModelOutput, ModelVersion,
)
from app.db.session import SessionLocal
from app.services.storage_service import get_storage_backend
from app.services.job_queue import get_queue

logger = logging.getLogger(__name__)


class MLDependencyUnavailable(RuntimeError):
    """Mimari için gerekli ML kütüphanesi (torch/ultralytics) kurulu değil
    veya o mimari için henüz sarmalayıcı yazılmadı. Job bunu yakalayıp
    'failed' yapar — backend/worker süreci çökmez."""


def _predict_yolo_det(model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int):
    try:
        from src.detection import predict_volume
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "ultralytics/torch bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    weights_path = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)
    return predict_volume(weights=weights_path, case_dir=case_dir, conf=conf_threshold, min_slice_run=min_slice_run)


_ARCHITECTURE_HANDLERS = {
    "yolo_det": _predict_yolo_det,
}


def run_architecture_inference(model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int):
    """Mimariye göre uygun `src/` fonksiyonunu çağırır. Dönüş: pandas.DataFrame
    (case, image_id, class, x1, y1, x2, y2, score) — `src.evaluation` ile aynı şema."""
    handler = _ARCHITECTURE_HANDLERS.get(model_version.architecture)
    if handler is None:
        raise MLDependencyUnavailable(
            f"'{model_version.architecture}' mimarisi için inference sarmalayıcısı henüz yazılmadı "
            "(plan Bölüm 4 tablosu — Faz 5 kapsamı)"
        )
    return handler(model_version, case, conf_threshold, min_slice_run)


# ---------------------------------------------------------------------------
# Tahmin sonuçlarını annotations + annotation_groups olarak yaz
# ---------------------------------------------------------------------------
def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def write_predictions_and_group(
    db: Session,
    *,
    case_id,
    model_output: ModelOutput,
    rows: list[dict],
    iou_threshold: float = 0.3,
) -> int:
    """`predict_volume` çıktısını annotations'a yazar, ardışık dilim +
    örtüşen bbox'ları (plan Bölüm 2 "2D/3D ayrımı") annotation_groups altında
    toplar. `rows`: [{"image_id":, "class":, "x1":, "y1":, "x2":, "y2":, "score":}, ...]
    image_id'ye göre sıralı olmalı."""
    rows = sorted(rows, key=lambda r: (int(r["class"]), int(r["image_id"])))
    created = 0
    i = 0
    while i < len(rows):
        run_rows = [rows[i]]
        j = i + 1
        while (
            j < len(rows)
            and rows[j]["class"] == rows[i]["class"]
            and int(rows[j]["image_id"]) - int(run_rows[-1]["image_id"]) == 1
            and _iou(
                (run_rows[-1]["x1"], run_rows[-1]["y1"], run_rows[-1]["x2"], run_rows[-1]["y2"]),
                (rows[j]["x1"], rows[j]["y1"], rows[j]["x2"], rows[j]["y2"]),
            ) >= iou_threshold
        ):
            run_rows.append(rows[j])
            j += 1

        group = None
        if len(run_rows) > 1:
            group = AnnotationGroup(
                case_id=case_id,
                class_type="lesion",
                class_id=int(run_rows[0]["class"]),
                geometry_type="bbox",
                source="prediction",
                model_output_id=model_output.id,
                z_start=int(run_rows[0]["image_id"]),
                z_end=int(run_rows[-1]["image_id"]),
                n_slices=len(run_rows),
            )
            db.add(group)
            db.flush()

        for r in run_rows:
            db.add(Annotation(
                case_id=case_id,
                image_id=int(r["image_id"]),
                class_type="lesion",
                class_id=int(r["class"]),
                geometry_type="bbox",
                geometry={"x1": r["x1"], "y1": r["y1"], "x2": r["x2"], "y2": r["y2"]},
                source="prediction",
                confidence=r.get("score"),
                model_output_id=model_output.id,
                group_id=group.id if group else None,
            ))
            created += 1
        i = j

    return created


def _update_batch_status(db: Session, batch_id) -> None:
    batch = db.get(InferenceBatch, batch_id)
    if batch is None:
        return
    runs = db.execute(select(InferenceRun).where(InferenceRun.batch_id == batch_id)).scalars().all()
    if any(r.status in ("queued", "running") for r in runs):
        return  # henüz bitmedi
    statuses = {r.status for r in runs}
    if statuses == {"succeeded"}:
        batch.status = "succeeded"
    elif statuses == {"failed"}:
        batch.status = "failed"
    else:
        batch.status = "partial"
    db.add(batch)
    db.commit()


# ---------------------------------------------------------------------------
# Batch oluşturma (API router ve dicom_ingest.py'nin otomatik tetiklemesi
# tarafından ortak kullanılır — plan Bölüm 4 "iki modlu inference")
# ---------------------------------------------------------------------------
def create_inference_batch(
    db: Session, *, case: Case, batch_type: str, model_versions: list[ModelVersion], actor_id
) -> InferenceBatch | None:
    if not model_versions:
        return None

    batch = InferenceBatch(case_id=case.id, batch_type=batch_type, triggered_by=actor_id, status="queued")
    db.add(batch)
    db.flush()

    queue = get_queue()
    for mv in model_versions:
        run = InferenceRun(
            batch_id=batch.id, case_id=case.id, model_version_id=mv.id,
            conf_threshold=0.2, min_slice_run=3, status="queued",
        )
        db.add(run)
        db.flush()
        job = queue.enqueue(run_inference_job, str(run.id))
        run.queue_job_id = job.id
        db.add(run)

    db.commit()
    return batch


def trigger_default_inference(db: Session, *, case: Case, actor_id) -> InferenceBatch | None:
    """Case `ready` olunca otomatik çağrılır (plan Bölüm 4: `run-default` —
    ek tıklama gerekmez). Aktif `run_mode='default'` model yoksa sessizce
    None döner; bu normal bir durumdur (henüz hiç model registry'ye
    eklenmemiş/aktifleştirilmemiş olabilir)."""
    model_versions = list(
        db.execute(
            select(ModelVersion).where(ModelVersion.run_mode == "default", ModelVersion.status == "active")
        ).scalars().all()
    )
    return create_inference_batch(db, case=case, batch_type="default", model_versions=model_versions, actor_id=actor_id)


# ---------------------------------------------------------------------------
# RQ job giriş noktası
# ---------------------------------------------------------------------------
def run_inference_job(inference_run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(InferenceRun, inference_run_id)
        if run is None:
            logger.error("run_inference_job: run bulunamadı id=%s", inference_run_id)
            return

        run.status = "running"
        db.add(run)
        db.commit()

        case = db.get(Case, run.case_id)
        model_version = db.get(ModelVersion, run.model_version_id)

        try:
            df = run_architecture_inference(
                model_version, case, float(run.conf_threshold), int(run.min_slice_run)
            )
            rows = df.to_dict("records") if df is not None and len(df) else []

            bbox_output = next((o for o in model_version.outputs if o.output_type == "bbox"), None)
            if bbox_output is None:
                raise MLDependencyUnavailable(
                    f"Model '{model_version.name}' için 'bbox' tipinde bir model_output tanımlı değil"
                )

            write_predictions_and_group(db, case_id=case.id, model_output=bbox_output, rows=rows)
            run.status = "succeeded"
            db.add(run)
            db.commit()
        except MLDependencyUnavailable as exc:
            run.status = "failed"
            run.error_message = str(exc)
            db.add(run)
            db.commit()
        except Exception as exc:  # noqa: BLE001 — job'ı düzgünce 'failed' yapmak için geniş yakalama
            logger.exception("run_inference_job hata: run=%s", inference_run_id)
            run.status = "failed"
            run.error_message = str(exc)[:1000]
            db.add(run)
            db.commit()

        _update_batch_status(db, run.batch_id)
    finally:
        db.close()
