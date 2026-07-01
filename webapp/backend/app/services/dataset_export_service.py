"""DB-native dataset snapshot oluşturma (plan Bölüm 6, adım 4).

approved_for_training durumundaki case'lerden ve included_in_training_pool=True
annotasyonlarından Bilgi.xlsx'e gerek kalmadan manifest üretir.
"""
from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Annotation, Case, CaseSlice, DatasetSnapshot
from app.services.storage_service import get_storage_backend

logger = logging.getLogger(__name__)


def build_snapshot(
    db: Session,
    *,
    snapshot_name: str,
    description: str | None,
    notes: str | None,
    actor_id: uuid.UUID,
    dataset_id: uuid.UUID | None = None,
) -> DatasetSnapshot:
    """
    approved_for_training case'lerinden ve eğitim havuzundaki annotasyonlardan
    JSON manifest oluşturur, storage'a kaydeder, DatasetSnapshot satırı döner.
    dataset_id verilirse sadece o veri setine ait case'ler dahil edilir.
    """
    # 1. Onaylı case'leri bul
    stmt = select(Case).where(Case.review_status == "approved_for_training")
    if dataset_id is not None:
        stmt = stmt.where(Case.dataset_id == dataset_id)
    approved_cases = db.execute(stmt).scalars().all()

    if not approved_cases:
        logger.warning("Snapshot için approved_for_training case bulunamadı.")

    case_ids = [c.id for c in approved_cases]

    # 2. Training pool annotasyonlarını al
    annotations_rows = []
    if case_ids:
        annotations_rows = db.execute(
            select(Annotation).where(
                Annotation.case_id.in_(case_ids),
                Annotation.included_in_training_pool == True,  # noqa: E712
                Annotation.status == "active",
                Annotation.geometry_type.in_(["bbox", "polygon"]),
            )
        ).scalars().all()

    # 3. Slice → png_storage_key eşlemesi
    slice_png: dict[tuple[uuid.UUID, int], str] = {}
    if case_ids:
        slices = db.execute(
            select(CaseSlice).where(CaseSlice.case_id.in_(case_ids))
        ).scalars().all()
        for s in slices:
            slice_png[(s.case_id, s.image_id)] = s.png_storage_key or ""

    # 4. case_id → annotasyon listesi (image_id bazında)
    ann_by_case_slice: dict[tuple[uuid.UUID, int], list[dict]] = {}
    for ann in annotations_rows:
        key = (ann.case_id, ann.image_id)
        ann_by_case_slice.setdefault(key, []).append({
            "annotation_id": str(ann.id),
            "class_id": ann.class_id,
            "class_type": ann.class_type,
            "geometry_type": ann.geometry_type,
            "geometry": ann.geometry,
        })

    # 5. Manifest yap
    manifest_cases: list[dict] = []
    for case in approved_cases:
        slices_data: list[dict] = []
        for (cid, img_id), anns in ann_by_case_slice.items():
            if cid != case.id:
                continue
            slices_data.append({
                "image_id": img_id,
                "png_storage_key": slice_png.get((case.id, img_id), ""),
                "annotations": anns,
            })

        if not slices_data:
            continue  # annotasyonsuz case'leri atlıyoruz

        slices_data.sort(key=lambda s: s["image_id"])
        manifest_cases.append({
            "case_id": str(case.id),
            "case_label": case.case_label or str(case.id),
            "slices": slices_data,
        })

    total_ann = sum(len(s["annotations"]) for c in manifest_cases for s in c["slices"])

    manifest = {
        "snapshot_name": snapshot_name,
        "total_cases": len(manifest_cases),
        "total_annotations": total_ann,
        "cases": manifest_cases,
    }

    # 6. Storage'a kaydet
    storage = get_storage_backend()
    key_prefix = f"snapshots/{uuid.uuid4().hex}"
    manifest_key = storage.save(
        f"{key_prefix}/manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2).encode(),
    )

    # 7. DB satırı oluştur
    snap = DatasetSnapshot(
        snapshot_name=snapshot_name,
        description=description,
        notes=notes,
        manifest_storage_key=manifest_key,
        included_cases_count=len(manifest_cases),
        included_annotations_count=total_ann,
        source="webapp",
        created_by=actor_id,
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    logger.info(
        "Snapshot oluşturuldu: name=%s cases=%d annotations=%d",
        snapshot_name, len(manifest_cases), total_ann,
    )
    return snap


def load_manifest(manifest_storage_key: str) -> dict:
    storage = get_storage_backend()
    return json.loads(storage.read(manifest_storage_key))
