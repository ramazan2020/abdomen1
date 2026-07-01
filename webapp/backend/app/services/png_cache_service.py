"""Lazy PNG önbellekleme (plan Bölüm 1).

İlk 20-30 dilim ingest sırasında senkron üretilir; kalanı `warm_png_cache`
arka plan job'ı doldurur. `get_or_generate_png_bytes` ise istek-üzerine
(cache miss durumunda) anlık üretim yapar — kullanıcı asla "veri yok" görmez.
"""
from __future__ import annotations

import io
import logging

import numpy as np
import pydicom
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.dicom_utils import dicom_to_hu, hu_to_three_channel

from app.db.models import CaseSlice
from app.db.session import SessionLocal
from app.services.storage_service import StorageBackend, get_storage_backend

logger = logging.getLogger(__name__)


def _png_key(case_id, image_id: int) -> str:
    return f"cases/{case_id}/png/{image_id}.png"


def _render_png_bytes(dicom_bytes: bytes) -> bytes:
    ds = pydicom.dcmread(io.BytesIO(dicom_bytes), force=True)
    hu = dicom_to_hu(ds)
    rgb = hu_to_three_channel(hu)  # (H, W, 3) float32 in [0, 1]
    arr = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="RGB").save(buf, format="PNG")
    return buf.getvalue()


def generate_and_cache_png(db: Session, storage: StorageBackend, case_slice: CaseSlice) -> str:
    dicom_bytes = storage.read(case_slice.dicom_storage_key)
    png_bytes = _render_png_bytes(dicom_bytes)
    key = _png_key(case_slice.case_id, case_slice.image_id)
    storage.save(key, png_bytes)
    case_slice.png_storage_key = key
    db.add(case_slice)
    return key


def get_or_generate_png_bytes(db: Session, case_slice: CaseSlice) -> bytes:
    storage = get_storage_backend()
    if case_slice.png_storage_key and storage.exists(case_slice.png_storage_key):
        return storage.read(case_slice.png_storage_key)
    key = generate_and_cache_png(db, storage, case_slice)
    db.commit()
    return storage.read(key)


def warm_png_cache(case_id: str) -> None:
    """RQ job: case'in kalan dilimlerini z-sırasıyla gezip önbelleği tamamlar."""
    db = SessionLocal()
    try:
        storage = get_storage_backend()
        slices = (
            db.execute(
                select(CaseSlice).where(CaseSlice.case_id == case_id).order_by(CaseSlice.z_index)
            )
            .scalars()
            .all()
        )
        for cs in slices:
            if cs.png_storage_key and storage.exists(cs.png_storage_key):
                continue
            try:
                generate_and_cache_png(db, storage, cs)
                db.commit()
            except Exception:
                logger.exception("warm_png_cache: dilim üretilemedi case=%s image_id=%s", case_id, cs.image_id)
                db.rollback()
    finally:
        db.close()
