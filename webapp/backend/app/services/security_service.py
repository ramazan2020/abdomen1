"""KVKK katmanı: de-identifikasyon kuralları (plan Bölüm 3).

Yükleme anında zorunlu — ham (kimlikli) DICOM hiçbir zaman diske/DB'ye yazılmaz.
"""
from __future__ import annotations

import secrets

import pydicom
from pydicom.dataset import FileDataset

# Doğrudan/dolaylı kimliklendirici DICOM etiketleri — ayrıştırma sırasında silinir.
_IDENTIFYING_TAGS: list[str] = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "PatientAddress",
    "PatientTelephoneNumbers",
    "OtherPatientIDs",
    "OtherPatientNames",
    "InstitutionName",
    "InstitutionAddress",
    "AccessionNumber",
    "ReferringPhysicianName",
    "PerformingPhysicianName",
    "OperatorsName",
    "RequestingPhysician",
    "StationName",
]


def deidentify_dataset(ds: FileDataset) -> FileDataset:
    """DICOM dataset üzerinde yerinde (in-place) de-identifikasyon uygular ve
    aynı nesneyi döner. Kimliklendirici alanlar tamamen silinir (boş string
    değil — `del` ile), böylece üretim DB/disk'inde asla iz kalmaz."""
    for tag in _IDENTIFYING_TAGS:
        if tag in ds:
            delattr(ds, tag)
    return ds


def generate_pseudonym() -> str:
    """`PAT-XXXXXX` biçiminde, gerçek kimlikle ilişkisiz bir takma ad üretir."""
    return f"PAT-{secrets.randbelow(900_000) + 100_000}"


def read_header_safely(path) -> FileDataset | None:
    """Bozuk dosyaları sessizce None döndürerek atlamak için — validation_report'taki
    'eksik/bozuk dosya sayısı' bu fonksiyonun None döndürdüğü dosyalardan sayılır."""
    try:
        return pydicom.dcmread(str(path), force=True)
    except Exception:
        return None
