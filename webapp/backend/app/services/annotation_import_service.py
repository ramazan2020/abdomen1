"""Annotation ZIP içe aktarma (plan Bölüm 6: dışa/içe aktarma kaçış yolu).

`webapp/scripts/make_annotation_zip.py` ile üretilen zip'leri (annotations.json
içeren) doğrudan webapp'e POST ile yükleyip eşleşen case'lere annotasyon
yazar. CLI script'leriyle (`import_annotation_zip.py`) AYNI mantığı kullanır,
böylece hem komut satırından hem web arayüzünden aynı sonuç elde edilir.

ZIP formatı (annotations.json):
    {"version": "1.0", "source": "train"|"comp", "cases": [
        {"case_num": "20001", "prefix": "T", "annotations": [
            {"webapp_image_id": 12, "class_id": 1, "geometry_type": "bbox",
             "geometry": {"x1":...,"y1":...,"x2":...,"y2":...}}
        ]}
    ]}
`webapp_image_id` zaten z-sıralaması çözümlenmiş olduğundan, import sırasında
orijinal DICOM dosyalarına ihtiyaç yoktur.
"""
from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Case, User
from app.services.annotation_service import create_manual_annotation

_GEOMETRY_TYPES = ("bbox", "polygon")


class AnnotationZipError(ValueError):
    pass


def _find_case_by_label(db: Session, case_key: str) -> Case | None:
    """case_label içinde TAM prefix'li anahtarı arar (örn. "T_20001").
    Bilerek çıplak case numarasıyla DEĞİL — Bilgi.xlsx'te aynı numara hem
    Egitim (T_) hem Test (C_) setinde farklı vakalara karşılık gelebilir
    (CLI script'leriyle aynı eşleşme mantığı, bkz. import_annotation_zip.py)."""
    candidates = db.execute(select(Case).where(Case.case_label.isnot(None))).scalars().all()
    for c in candidates:
        if case_key in (c.case_label or ""):
            return c
    return None


def import_annotation_zip(db: Session, *, zip_bytes: bytes, actor: User) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            if "annotations.json" not in zf.namelist():
                raise AnnotationZipError("ZIP içinde 'annotations.json' bulunamadı")
            data = json.loads(zf.read("annotations.json").decode("utf-8"))
    except zipfile.BadZipFile as exc:
        raise AnnotationZipError("Geçersiz zip dosyası") from exc
    except json.JSONDecodeError as exc:
        raise AnnotationZipError(f"annotations.json çözümlenemedi: {exc}") from exc

    cases = data.get("cases")
    if not isinstance(cases, list):
        raise AnnotationZipError("annotations.json formatı geçersiz: 'cases' listesi bekleniyor")

    total_sent = 0
    total_skipped = 0
    details: list[dict[str, Any]] = []

    for case_entry in cases:
        case_num = str(case_entry.get("case_num", ""))
        prefix = case_entry.get("prefix", "T")
        case_key = f"{prefix}_{case_num}"
        annotations = case_entry.get("annotations", [])

        if not annotations:
            details.append({"case_num": case_num, "prefix": prefix, "matched": None, "sent": 0, "skipped": 0})
            continue

        webapp_case = _find_case_by_label(db, case_key)
        if webapp_case is None:
            total_skipped += len(annotations)
            details.append({
                "case_num": case_num, "prefix": prefix, "matched": False,
                "sent": 0, "skipped": len(annotations),
                "note": f"case_label '{case_key}' içeren bir vaka bulunamadı",
            })
            continue

        sent = skipped = 0
        for ann in annotations:
            geometry_type = ann.get("geometry_type")
            if geometry_type not in _GEOMETRY_TYPES:
                skipped += 1
                continue
            try:
                create_manual_annotation(
                    db,
                    case_id=webapp_case.id,
                    actor=actor,
                    image_id=int(ann["webapp_image_id"]),
                    class_type="lesion",
                    class_id=int(ann["class_id"]),
                    geometry_type=geometry_type,
                    geometry=ann["geometry"],
                )
                sent += 1
            except (KeyError, ValueError, TypeError):
                skipped += 1

        total_sent += sent
        total_skipped += skipped
        details.append({
            "case_num": case_num, "prefix": prefix, "matched": True,
            "case_id": str(webapp_case.id), "sent": sent, "skipped": skipped,
        })

    return {"total_sent": total_sent, "total_skipped": total_skipped, "details": details}
