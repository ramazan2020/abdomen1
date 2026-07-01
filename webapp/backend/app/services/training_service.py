"""Eğitim iş orkestrasyonu (plan Bölüm 4, madde 3).

Uzun süren eğitim işleri için:
- heartbeat_at periyodik güncelleme (donmuş job tespiti)
- cancel_requested bayrağı kontrolü
- ultralytics epoch callback ile progress_percent / current_epoch / best_metric
- MLDependencyUnavailable ile graceful fail (GPU/torch olmayan ortam)
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import ModelOutput, ModelVersion, TrainingJob
from app.db.session import SessionLocal
from app.services.dataset_export_service import load_manifest
from app.services.inference_service import MLDependencyUnavailable
from app.services.job_queue import get_queue
from app.services.storage_service import get_storage_backend

logger = logging.getLogger(__name__)

_SUPPORTED_ARCH = {"yolo_det", "yolo_seg"}
_DEFAULT_PARAMS: dict = {
    "model":   "yolov8s.pt",
    "epochs":  50,
    "imgsz":   512,
    "batch":   16,
    "patience": 20,
}


# ── Job oluşturma (API katmanı çağırır) ──────────────────────────────────────

def create_training_job(
    db: Session,
    *,
    snapshot_id: uuid.UUID,
    architecture: str,
    params: dict,
    actor_id: uuid.UUID,
) -> TrainingJob:
    if architecture not in _SUPPORTED_ARCH:
        raise ValueError(
            f"Desteklenmeyen mimari: {architecture!r}. "
            f"Desteklenenler: {', '.join(sorted(_SUPPORTED_ARCH))}"
        )

    merged_params = {**_DEFAULT_PARAMS, **params}

    job = TrainingJob(
        job_type=f"train_{architecture.split('_', 1)[-1]}",
        architecture=architecture,
        params=merged_params,
        dataset_snapshot_id=snapshot_id,
        triggered_by=actor_id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q = get_queue()
    rq_job = q.enqueue(
        "app.services.training_service.run_training_job",
        str(job.id),
        job_timeout=86_400,
        result_ttl=3_600,
    )
    job.queue_job_id = rq_job.id
    db.commit()

    logger.info("Training job kuyruğa alındı: id=%s arch=%s", job.id, architecture)
    return job


# ── RQ worker entry point ────────────────────────────────────────────────────

def run_training_job(job_id: str) -> None:
    """RQ tarafından çağrılır. Her aşama DB'yi heartbeat ile günceller."""
    log_path = _log_path(job_id)
    _log(log_path, f"=== Training job başladı: {job_id} ===")

    # ── Başlangıç durumu ───────────────────────────────────────────
    with SessionLocal() as db:
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job is None:
            logger.error("TrainingJob bulunamadı: %s", job_id)
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.heartbeat_at = datetime.now(timezone.utc)
        job.log_storage_key = f"training/{job_id}/train.log"
        architecture = job.architecture
        params = dict(job.params or {})
        snapshot_id = str(job.dataset_snapshot_id)
        db.commit()

    try:
        # ── 1. Manifest yükle ──────────────────────────────────────
        _log(log_path, "Dataset snapshot manifest yükleniyor...")
        with SessionLocal() as db:
            from app.db.models import DatasetSnapshot
            snap = db.get(DatasetSnapshot, uuid.UUID(snapshot_id))
            manifest_key = snap.manifest_storage_key
            snap_name = snap.snapshot_name

        manifest = load_manifest(manifest_key)
        _log(log_path, (
            f"Snapshot: {snap_name} | "
            f"case={manifest['total_cases']} | "
            f"ann={manifest['total_annotations']}"
        ))

        # ── 2. İptal kontrolü ─────────────────────────────────────
        if _check_cancel(job_id, log_path):
            return

        # ── 3. YOLO dataset dizini oluştur ─────────────────────────
        _log(log_path, "YOLO dataset dışa aktarılıyor...")
        dataset_dir = _build_yolo_dataset(job_id, manifest, architecture, log_path)
        _log(log_path, f"Dataset hazır: {dataset_dir}")
        _heartbeat(job_id, progress_percent=10.0)

        # ── 4. İptal kontrolü ─────────────────────────────────────
        if _check_cancel(job_id, log_path):
            return

        # ── 5. Eğitim çalıştır ────────────────────────────────────
        best_weights = _train(job_id, architecture, params, dataset_dir, log_path)

        # ── 6. Model kaydet ───────────────────────────────────────
        _log(log_path, f"Eğitim tamamlandı. Best: {best_weights}")
        new_mv_id = _register_model(job_id, architecture, params, best_weights, snap_name)
        _log(log_path, f"Yeni model kaydedildi: {new_mv_id}")

        with SessionLocal() as db:
            job = db.get(TrainingJob, uuid.UUID(job_id))
            job.status = "succeeded"
            job.finished_at = datetime.now(timezone.utc)
            job.progress_percent = 100.0
            job.result_model_version_id = new_mv_id
            db.commit()

        _log(log_path, "=== Job BAŞARILI ===")

    except MLDependencyUnavailable as exc:
        msg = f"ML bağımlılığı eksik — {exc}"
        _log(log_path, f"HATA: {msg}")
        _fail_job(job_id, msg)

    except Exception as exc:
        msg = str(exc)[:1000]
        _log(log_path, f"HATA: {msg}")
        logger.exception("Training job başarısız: %s", job_id)
        _fail_job(job_id, msg)


# ── Yardımcı fonksiyonlar ────────────────────────────────────────────────────

def _log_path(job_id: str) -> Path:
    storage = get_storage_backend()
    try:
        p = Path(storage.local_path(f"training/{job_id}/train.log"))
    except Exception:
        p = Path(f"/tmp/train_{job_id}.log")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _log(path: Path, msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    logger.info(line)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _heartbeat(job_id: str, **updates) -> None:
    with SessionLocal() as db:
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job is None:
            return
        job.heartbeat_at = datetime.now(timezone.utc)
        for k, v in updates.items():
            setattr(job, k, v)
        db.commit()


def _check_cancel(job_id: str, log_path: Path) -> bool:
    with SessionLocal() as db:
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job and job.cancel_requested:
            _log(log_path, "İptal isteği algılandı.")
            job.status = "cancelled"
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            return True
    return False


def _fail_job(job_id: str, error: str) -> None:
    with SessionLocal() as db:
        job = db.get(TrainingJob, uuid.UUID(job_id))
        if job:
            job.status = "failed"
            job.error_message = error
            job.finished_at = datetime.now(timezone.utc)
            db.commit()


def _build_yolo_dataset(
    job_id: str, manifest: dict, architecture: str, log_path: Path
) -> Path:
    """Manifest'ten YOLO/YOLOSeg formatında dosya yapısı oluştur."""
    import io as _io
    from PIL import Image as PILImage

    storage = get_storage_backend()
    is_seg = "seg" in architecture

    base: Path = Path(storage.local_path(f"training/{job_id}/dataset"))
    for split in ("train", "val"):
        (base / "images" / split).mkdir(parents=True, exist_ok=True)
        (base / "labels" / split).mkdir(parents=True, exist_ok=True)

    cases = manifest["cases"]
    val_n = max(1, len(cases) // 5)
    class_ids: set[int] = set()

    for idx, case in enumerate(cases):
        split = "val" if idx < val_n else "train"
        label = case["case_label"]

        for sl in case["slices"]:
            img_id: int = sl["image_id"]
            png_key: str = sl["png_storage_key"]
            anns: list[dict] = sl["annotations"]

            if not anns:
                continue

            stem = f"{label}_{img_id:04d}"

            # PNG oku
            try:
                if png_key:
                    img = PILImage.open(_io.BytesIO(storage.read(png_key))).convert("RGB")
                else:
                    _log(log_path, f"  PNG yok, atlıyor: {label}/{img_id}")
                    continue
            except Exception as exc:
                _log(log_path, f"  PNG okunamadı {label}/{img_id}: {exc}")
                continue

            w, h = img.size
            img.save(str(base / "images" / split / f"{stem}.png"))

            with (base / "labels" / split / f"{stem}.txt").open("w") as lf:
                for ann in anns:
                    cid = ann["class_id"]
                    class_ids.add(cid)
                    gtype = ann["geometry_type"]
                    g = ann["geometry"]

                    if gtype == "bbox":
                        x1, y1, x2, y2 = g["x1"], g["y1"], g["x2"], g["y2"]
                        cx = (x1 + x2) / 2 / w
                        cy = (y1 + y2) / 2 / h
                        bw = (x2 - x1) / w
                        bh = (y2 - y1) / h
                        lf.write(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

                    elif gtype == "polygon" and is_seg:
                        pts = g.get("points", [])
                        if len(pts) >= 3:
                            coords = " ".join(f"{p[0]/w:.6f} {p[1]/h:.6f}" for p in pts)
                            lf.write(f"{cid} {coords}\n")

    # dataset.yaml
    nc = (max(class_ids) + 1) if class_ids else 1
    from app.core.config import get_settings
    settings = get_settings()
    nc_override = len(settings.super_classes) if hasattr(settings, "super_classes") else nc
    nc = max(nc, nc_override) if nc_override > 0 else nc

    yaml_lines = [
        f"path: {base}",
        "train: images/train",
        "val:   images/val",
        f"nc: {nc}",
        "names:",
    ]
    # src/config.py SUPER_CLASSES uyumlu adlandırma (varsa)
    super_class_names = [
        "acute_cholecystitis", "kidney_ureter_stone", "acute_pancreatitis",
        "aortic_aneurysm_dissection", "acute_appendicitis", "acute_diverticulitis",
    ]
    for i in range(nc):
        name = super_class_names[i] if i < len(super_class_names) else f"class_{i}"
        yaml_lines.append(f"  {i}: {name}")

    (base / "dataset.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    _log(log_path, f"dataset.yaml: nc={nc}, split: train={len(cases)-val_n}, val={val_n}")
    return base


def _train(
    job_id: str, architecture: str, params: dict, dataset_dir: Path, log_path: Path
) -> Path:
    """YOLO eğitim loop. heartbeat + cancel callback içerir."""
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise MLDependencyUnavailable("ultralytics bu ortamda kurulu değil") from exc

    model_name = params.get("model", "yolov8s.pt")
    epochs     = int(params.get("epochs", 50))
    imgsz      = int(params.get("imgsz", 512))
    batch      = int(params.get("batch", 16))
    patience   = int(params.get("patience", 20))
    task       = "segment" if "seg" in architecture else "detect"

    _log(log_path, f"YOLO.train başlıyor: model={model_name} epochs={epochs} task={task}")
    model = YOLO(model_name)

    def _epoch_cb(trainer) -> None:
        epoch = trainer.epoch + 1
        progress = 10 + (epoch / epochs) * 80
        metrics = {
            k: float(v)
            for k, v in trainer.metrics.items()
            if isinstance(v, (int, float))
        }
        _log(log_path, f"Epoch {epoch}/{epochs} | {metrics}")
        _heartbeat(
            job_id,
            progress_percent=round(progress, 1),
            current_epoch=epoch,
            best_metric=metrics,
        )
        # Cancel kontrolü
        with SessionLocal() as _db:
            j = _db.get(TrainingJob, uuid.UUID(job_id))
            if j and j.cancel_requested:
                _log(log_path, "Epoch callback: iptal isteği — trainer.stop=True")
                trainer.stop = True

    model.add_callback("on_train_epoch_end", _epoch_cb)

    project_root = dataset_dir.parent / "runs"
    run_name = f"job_{job_id[:8]}"

    model.train(
        data=str(dataset_dir / "dataset.yaml"),
        task=task,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        patience=patience,
        project=str(project_root),
        name=run_name,
        exist_ok=True,
        verbose=True,
    )

    best = project_root / run_name / "weights" / "best.pt"
    if not best.exists():
        best = project_root / run_name / "weights" / "last.pt"
    if not best.exists():
        raise FileNotFoundError(f"Eğitim bitti ama weights bulunamadı: {project_root / run_name}")

    return best


def _register_model(
    job_id: str,
    architecture: str,
    params: dict,
    weights_path: Path,
    snap_name: str,
) -> uuid.UUID:
    """Eğitim sonucu model_versions'a kaydeder, id döner."""
    storage = get_storage_backend()
    weights_bytes = weights_path.read_bytes()
    mv_uuid = uuid.uuid4()
    storage_key = storage.save(f"models/{mv_uuid}/best.pt", weights_bytes)

    model_label = params.get("model", "yolov8s.pt")
    version_name = f"{architecture}-{snap_name[:24]}"
    output_type = "mask" if "seg" in architecture else "bbox"

    with SessionLocal() as db:
        mv = ModelVersion(
            id=mv_uuid,
            name=version_name,
            architecture=architecture,
            run_mode="comparison",
            weights_storage_key=storage_key,
            base_weights=model_label,
            status="inactive",
        )
        db.add(mv)
        db.flush()

        db.add(ModelOutput(
            model_version_id=mv.id,
            output_type=output_type,
            class_set=None,
            postprocess_config={"conf_threshold": 0.25, "min_slice_run": 3},
        ))
        db.commit()

    return mv_uuid
