"""DICOM ingest: zip -> doğrulanmış, de-identifiye edilmiş case dizini (plan Bölüm 1/3/4).

`ingest_case` bir RQ job'ı olarak çalışır (kendi DB session'ını açar). Akış:
  1. Yüklenen zip'i geçici bir dizine aç
  2. Her dosyayı DICOM olarak okumayı dener (bozuk/eksik dosyalar sayılır)
  3. Geçerli kesitleri z-pozisyonuna göre sıralar, image_id = 0..N-1 atar
     (src.dicom_utils.DicomVolume ile aynı "{image_id}.dcm" konvansiyonu)
  4. Her kesiti de-identifiye edip storage'a yazar, case_slices satırı oluşturur
  5. validation_report'u hesaplar (toplam/geçerli/bozuk sayım, slice thickness,
     pixel spacing, series description, de-identification durumu)
  6. İlk N dilimi senkron PNG önbelleğe alır, kalanı warm_png_cache job'ına bırakır
  7. Ham (kimlikli) zip'i storage'dan siler — KVKK: minimum saklama
"""
from __future__ import annotations

import io
import logging
import tempfile
import zipfile
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Case, CaseSlice
from app.db.session import SessionLocal
from app.services.security_service import deidentify_dataset

logger = logging.getLogger(__name__)


def _upload_zip_key(case_id: str) -> str:
    return f"uploads/{case_id}.zip"


def _extract_zip(zip_bytes: bytes, dest_dir: Path) -> list[Path]:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(dest_dir)
    return [p for p in dest_dir.rglob("*") if p.is_file() and not p.name.startswith(".")]


def _read_all_candidates(paths: list[Path]):
    """Her dosyayı DICOM olarak okumayı dener. (dataset, path) listesi + bozuk sayısını döner.

    İki aşamalı okuma: doğrulama için stop_before_pixels=True (hızlı, sıkıştırma açılmaz),
    kaydetme için tam okuma. Bu sayede JPEG-2000 gibi sıkıştırılmış DICOM'lar false-invalid
    sayılmaz (piksel çözümlemesi PNG üretiminde lazy olarak yapılır, hata orada yönetilir).
    """
    import pydicom

    valid: list[tuple] = []
    invalid_count = 0
    for p in paths:
        try:
            # Header-only okuma: sıkıştırma açılmaz, transfer sözdizimi sorunları önemsiz
            ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
            # Minimal DICOM-CT geçerlilik kontrolü: sıralama için gereken alan var mı?
            if not (hasattr(ds, "ImagePositionPatient") or hasattr(ds, "InstanceNumber")):
                # Ne z-koordinatı ne de instance numarası var — gerçek görüntü DICOM değil
                invalid_count += 1
                continue
            # file_meta güvenlik ağı (src.dicom_utils.read_dicom ile aynı)
            if not hasattr(ds, "file_meta"):
                ds.file_meta = pydicom.Dataset()
            if not hasattr(ds.file_meta, "TransferSyntaxUID"):
                ds.file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
            valid.append((ds, p))
        except Exception:
            invalid_count += 1
    return valid, invalid_count


def _sort_by_z(valid: list[tuple]) -> tuple[list[tuple], str]:
    if all(hasattr(ds, "ImagePositionPatient") for ds, _ in valid):
        valid.sort(key=lambda t: float(t[0].ImagePositionPatient[2]))
        return valid, "ImagePositionPatient.z"
    if all(hasattr(ds, "InstanceNumber") for ds, _ in valid):
        valid.sort(key=lambda t: int(ds_instance_number(t[0])))
        return valid, "InstanceNumber"
    valid.sort(key=lambda t: t[1].name)
    return valid, "filename"


def ds_instance_number(ds) -> int:
    try:
        return int(ds.InstanceNumber)
    except Exception:
        return 0


def _build_validation_report(
    total_files: int,
    valid_count: int,
    invalid_count: int,
    sort_key: str,
    first_ds,
) -> dict:
    slice_thickness = None
    pixel_spacing = None
    series_description = None
    if first_ds is not None:
        try:
            slice_thickness = float(first_ds.SliceThickness)
        except Exception:
            slice_thickness = None
        try:
            pixel_spacing = [float(v) for v in first_ds.PixelSpacing]
        except Exception:
            pixel_spacing = None
        series_description = str(getattr(first_ds, "SeriesDescription", "") or "") or None

    return {
        "total_dicom_count": total_files,
        "valid_slice_count": valid_count,
        "invalid_file_count": invalid_count,
        "slice_thickness_mm": slice_thickness,
        "pixel_spacing_mm": pixel_spacing,
        "series_description": series_description,
        "sort_key": sort_key,
        "deidentification_status": "completed",
    }


def ingest_case(case_id: str) -> None:
    from app.services.png_cache_service import generate_and_cache_png, warm_png_cache
    from app.services.storage_service import get_storage_backend

    settings = get_settings()
    storage = get_storage_backend()
    db = SessionLocal()
    try:
        case = db.get(Case, case_id)
        if case is None:
            logger.error("ingest_case: case bulunamadı id=%s", case_id)
            return

        case.status = "validating"
        db.add(case)
        db.commit()

        zip_key = _upload_zip_key(case_id)
        try:
            zip_bytes = storage.read(zip_key)
        except FileNotFoundError:
            case.status = "failed"
            case.validation_report = {"error": "Yüklenen zip dosyası bulunamadı"}
            db.add(case)
            db.commit()
            return

        with tempfile.TemporaryDirectory(prefix=f"case_{case_id}_") as tmp:
            tmp_dir = Path(tmp)
            try:
                all_files = _extract_zip(zip_bytes, tmp_dir)
            except zipfile.BadZipFile:
                case.status = "failed"
                case.validation_report = {"error": "Geçersiz zip dosyası"}
                db.add(case)
                db.commit()
                return

            valid, invalid_count = _read_all_candidates(all_files)
            total_files = len(all_files)

            if not valid:
                case.status = "failed"
                case.validation_report = _build_validation_report(
                    total_files, 0, invalid_count, "-", None
                )
                db.add(case)
                db.commit()
                return

            valid, sort_key = _sort_by_z(valid)

            slices: list[CaseSlice] = []
            for image_id, (ds, orig_path) in enumerate(valid):
                # `ds` stop_before_pixels=True ile okundu (piksel verisi yok).
                # De-identifikasyon + kaydetme için tam dosyayı yeniden okuyoruz.
                import pydicom as _pd
                import warnings as _w
                with _w.catch_warnings():
                    _w.filterwarnings("ignore")
                    full_ds = _pd.dcmread(str(orig_path), force=True)
                if not hasattr(full_ds, "file_meta"):
                    full_ds.file_meta = _pd.Dataset()
                if not hasattr(full_ds.file_meta, "TransferSyntaxUID"):
                    full_ds.file_meta.TransferSyntaxUID = _pd.uid.ExplicitVRLittleEndian
                deidentify_dataset(full_ds)
                buf = io.BytesIO()
                # write_like_original=True: orijinal transfer sözdizimini (JPEG 2000 vb.)
                # değiştirmeden koru — sadece hasta etiketleri kaldırılmış haliyle kaydet.
                full_ds.save_as(buf, write_like_original=True)
                dicom_key = f"cases/{case_id}/dicom/{image_id}.dcm"
                storage.save(dicom_key, buf.getvalue())
                slices.append(
                    CaseSlice(
                        case_id=case.id,
                        image_id=image_id,
                        z_index=image_id,
                        dicom_storage_key=dicom_key,
                    )
                )

            db.add_all(slices)
            case.n_slices = len(slices)
            case.deidentified = True
            case.validation_report = _build_validation_report(
                total_files, len(valid), invalid_count, sort_key, valid[0][0]
            )
            case.status = "ready"
            db.add(case)
            db.commit()

            # İlk N dilimi senkron önbelleğe al (doktor hemen görüntüleyebilsin)
            for cs in slices[: settings.png_cache_warmup_slices]:
                try:
                    generate_and_cache_png(db, storage, cs)
                except Exception:
                    logger.exception("İlk PNG önbellekleme başarısız: case=%s image_id=%s", case_id, cs.image_id)
            db.commit()

        # Kalan dilimleri arka planda doldur (plan Bölüm 1: lazy + warm cache)
        from app.services.job_queue import get_queue

        get_queue().enqueue(warm_png_cache, str(case.id))

        # Plan Bölüm 4: case 'ready' olunca run-default otomatik tetiklenir
        # (aktif default model yoksa sessizce no-op — henüz registry boş olabilir).
        if case.status == "ready":
            from app.services.inference_service import trigger_default_inference

            try:
                trigger_default_inference(db, case=case, actor_id=case.uploaded_by)
            except Exception:
                logger.exception("Otomatik run-default tetiklenemedi: case=%s", case_id)
    finally:
        # Ham (kimliklendirilmemiş) zip hiçbir zaman uzun süre tutulmaz (KVKK).
        try:
            storage.delete(_upload_zip_key(case_id))
        except Exception:
            pass
        db.close()
