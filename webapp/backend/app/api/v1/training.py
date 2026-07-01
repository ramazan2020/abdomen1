"""Eğitim orkestrasyonu API (plan Bölüm 4, Faz 3).

Endpoint'ler:
  POST /training/snapshots          — dataset snapshot oluştur (admin)
  GET  /training/snapshots          — snapshot listesi
  GET  /training/snapshots/{id}     — snapshot detayı
  POST /training/jobs               — eğitim job başlat (admin)
  GET  /training/jobs               — job listesi
  GET  /training/jobs/{id}          — job durum + ilerleme
  GET  /training/jobs/{id}/logs     — log içeriği (polling)
  POST /training/jobs/{id}/cancel   — iptal isteği (admin)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import csv
import io
import json as _json
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_admin, require_doctor_or_admin
from app.db.models import Annotation, Case, DatasetSnapshot, TrainingJob, User
from app.schemas.training import (
    CreateSnapshotRequest,
    LaunchJobRequest,
    SnapshotDto,
    TrainingJobDto,
)
from app.services import dataset_export_service, training_service
from app.services.storage_service import get_storage_backend

router = APIRouter(prefix="/training", tags=["training"])


# ── İstatistikler ─────────────────────────────────────────────────────────────

@router.get("/stats")
def get_training_stats(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
) -> dict:
    """Eğitim havuzu istatistikleri: case review_status dağılımı + annotation havuzu + sınıf dağılımı."""
    # Case review_status sayımı
    review_rows = db.execute(
        select(Case.review_status, func.count(Case.id).label("n"))
        .group_by(Case.review_status)
    ).all()
    review_counts = {r.review_status: r.n for r in review_rows}

    # Havuzdaki annotation sayısı (active + included_in_training_pool)
    pool_total = db.execute(
        select(func.count(Annotation.id)).where(
            Annotation.status == "active",
            Annotation.included_in_training_pool.is_(True),
        )
    ).scalar() or 0

    # Sınıf dağılımı (havuzdaki, active)
    class_rows = db.execute(
        select(Annotation.class_id, func.count(Annotation.id).label("n"))
        .where(
            Annotation.status == "active",
            Annotation.included_in_training_pool.is_(True),
        )
        .group_by(Annotation.class_id)
        .order_by(Annotation.class_id)
    ).all()
    class_distribution = {str(r.class_id): r.n for r in class_rows}

    return {
        "review_status_counts": review_counts,
        "pool_annotation_count": pool_total,
        "class_distribution": class_distribution,
    }


# ── Snapshot ─────────────────────────────────────────────────────────────────

@router.post("/snapshots", response_model=SnapshotDto, status_code=status.HTTP_201_CREATED)
def create_snapshot(
    body: CreateSnapshotRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    try:
        ds_id = uuid.UUID(body.dataset_id) if body.dataset_id else None
        snap = dataset_export_service.build_snapshot(
            db,
            snapshot_name=body.snapshot_name,
            description=body.description,
            notes=body.notes,
            actor_id=actor.id,
            dataset_id=ds_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _snap_dto(snap)


@router.get("/snapshots", response_model=list[SnapshotDto])
def list_snapshots(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    rows = db.execute(
        select(DatasetSnapshot).order_by(desc(DatasetSnapshot.created_at))
    ).scalars().all()
    return [_snap_dto(r) for r in rows]


@router.get("/snapshots/{snapshot_id}/export")
def export_snapshot(
    snapshot_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Response:
    """Snapshot annotasyonlarını zip olarak indir: manifest.json + annotations.csv + YOLO labels."""
    snap = db.get(DatasetSnapshot, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Snapshot bulunamadı")
    if not snap.manifest_storage_key:
        raise HTTPException(status_code=422, detail="Snapshot manifest'i bulunamadı")

    manifest = dataset_export_service.load_manifest(snap.manifest_storage_key)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", _json.dumps(manifest, ensure_ascii=False, indent=2))

        csv_buf = io.StringIO()
        writer = csv.writer(csv_buf)
        writer.writerow(["case_id", "case_label", "image_id", "class_id", "geometry_type", "x1", "y1", "x2", "y2"])
        for case_data in manifest.get("cases", []):
            for s in case_data.get("slices", []):
                for ann in s.get("annotations", []):
                    geo = ann.get("geometry", {})
                    if ann.get("geometry_type") == "bbox":
                        writer.writerow([
                            case_data["case_id"], case_data.get("case_label", ""),
                            s["image_id"], ann["class_id"], "bbox",
                            geo.get("x1", ""), geo.get("y1", ""),
                            geo.get("x2", ""), geo.get("y2", ""),
                        ])
        zf.writestr("annotations.csv", csv_buf.getvalue())

        for case_data in manifest.get("cases", []):
            label = case_data.get("case_label", case_data["case_id"])
            for s in case_data.get("slices", []):
                lines = []
                for ann in s.get("annotations", []):
                    if ann.get("geometry_type") == "bbox":
                        geo = ann.get("geometry", {})
                        lines.append(
                            f"{ann['class_id']} {geo.get('x1', 0):.2f} {geo.get('y1', 0):.2f} "
                            f"{geo.get('x2', 0):.2f} {geo.get('y2', 0):.2f}"
                        )
                if lines:
                    zf.writestr(f"labels/{label}_{s['image_id']}.txt", "\n".join(lines))

    snap_name = snap.snapshot_name.replace(" ", "_")
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="snapshot_{snap_name}.zip"'},
    )


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotDto)
def get_snapshot(
    snapshot_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    snap = db.get(DatasetSnapshot, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail="Snapshot bulunamadı")
    return _snap_dto(snap)


# ── Training jobs ─────────────────────────────────────────────────────────────

@router.post("/jobs", response_model=TrainingJobDto, status_code=status.HTTP_201_CREATED)
def launch_job(
    body: LaunchJobRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    try:
        snap_id = uuid.UUID(body.snapshot_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Geçersiz snapshot_id formatı")

    if db.get(DatasetSnapshot, snap_id) is None:
        raise HTTPException(status_code=404, detail="Snapshot bulunamadı")

    try:
        job = training_service.create_training_job(
            db,
            snapshot_id=snap_id,
            architecture=body.architecture,
            params=body.params,
            actor_id=actor.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return _job_dto(job)


@router.get("/jobs", response_model=list[TrainingJobDto])
def list_jobs(
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    rows = db.execute(
        select(TrainingJob).order_by(desc(TrainingJob.created_at))
    ).scalars().all()
    return [_job_dto(r) for r in rows]


@router.get("/jobs/{job_id}", response_model=TrainingJobDto)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_doctor_or_admin),
):
    job = db.get(TrainingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return _job_dto(job)


@router.get("/jobs/{job_id}/logs", response_class=PlainTextResponse)
def get_job_logs(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_doctor_or_admin),
):
    job = db.get(TrainingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")

    if not job.log_storage_key:
        return "Henüz log yok."

    storage = get_storage_backend()
    try:
        if not storage.exists(job.log_storage_key):
            return "Log dosyası henüz oluşturulmadı."
        return storage.read(job.log_storage_key).decode("utf-8", errors="replace")
    except Exception as exc:
        return f"Log okunamadı: {exc}"


@router.post("/jobs/{job_id}/cancel", response_model=TrainingJobDto)
def cancel_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    job = db.get(TrainingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")

    if job.status not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"İptal edilemez: mevcut durum={job.status}",
        )

    job.cancel_requested = True
    if job.status == "queued":
        # Worker henüz başlatmadı — doğrudan iptal et
        job.status = "cancelled"
    db.commit()
    db.refresh(job)
    return _job_dto(job)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_admin),
):
    """Yalnızca failed veya cancelled jobları siler."""
    job = db.get(TrainingJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(
            status_code=400,
            detail=f"Yalnızca failed/cancelled joblar silinebilir (mevcut: {job.status})",
        )
    db.delete(job)
    db.commit()


# ── DTO dönüştürücüler ────────────────────────────────────────────────────────

def _snap_dto(snap: DatasetSnapshot) -> SnapshotDto:
    return SnapshotDto(
        id=str(snap.id),
        snapshot_name=snap.snapshot_name,
        description=snap.description,
        notes=snap.notes,
        included_cases_count=snap.included_cases_count,
        included_annotations_count=snap.included_annotations_count,
        source=snap.source,
        manifest_storage_key=snap.manifest_storage_key,
        created_at=snap.created_at.isoformat(),
    )


def _job_dto(job: TrainingJob) -> TrainingJobDto:
    return TrainingJobDto(
        id=str(job.id),
        job_type=job.job_type,
        architecture=job.architecture,
        params=job.params or {},
        dataset_snapshot_id=str(job.dataset_snapshot_id),
        status=job.status,
        progress_percent=float(job.progress_percent) if job.progress_percent is not None else None,
        current_epoch=job.current_epoch,
        best_metric=job.best_metric,
        error_message=job.error_message,
        cancel_requested=job.cancel_requested,
        log_storage_key=job.log_storage_key,
        queue_job_id=job.queue_job_id,
        started_at=job.started_at.isoformat() if job.started_at else None,
        finished_at=job.finished_at.isoformat() if job.finished_at else None,
        heartbeat_at=job.heartbeat_at.isoformat() if job.heartbeat_at else None,
        result_model_version_id=str(job.result_model_version_id) if job.result_model_version_id else None,
        created_at=job.created_at.isoformat(),
    )
