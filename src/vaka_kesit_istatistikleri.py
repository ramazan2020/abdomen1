"""
Vaka başına kesit istatistikleri:
  1) Annotasyonlu kesit sayısı (medyan) — Bilgi.xlsx'ten
  2) Toplam DICOM kesit sayısı (medyan ve maks) — dosya sisteminden
"""
import os
from pathlib import Path
import pandas as pd

# ---- YOLLAR ----
BASE = Path(os.environ.get(
    "TR_ABDOMEN_BASE",
    r"/Users/ramazanpolat/Desktop/datasets/abdomen"
))

    
XLSX = BASE / "Bilgi.xlsx"
DIRS = {
    "Eğitim":  BASE / "Eğitim Verisi.zip",   # açılmış dizin
    "Yarışma": BASE / "Yarışma Veri Seti",
}

# =========================================================
# 1) ANNOTASYONLU KESİT SAYISI (Bilgi.xlsx'ten)
#    Her vakada KAÇ tekil Image Id annotasyonlu? Medyanı al.
# =========================================================
sheets = pd.read_excel(XLSX, sheet_name=None)

print("=" * 60)
print("Vaka başına ANNOTASYONLU KESİT sayısı (Bilgi.xlsx)")
print("=" * 60)

for sheet_name, df in sheets.items():
    # Her Case Number için kaç farklı Image Id annotasyonlu?
    annotated_per_case = df.groupby("Case Number")["Image Id"].nunique()

    print(f"\n--- {sheet_name} ---")
    print(f"  Vaka sayısı           : {len(annotated_per_case)}")
    print(f"  Medyan (annotasyonlu) : {int(annotated_per_case.median())}")
    print(f"  Ortalama              : {annotated_per_case.mean():.1f}")
    print(f"  Min / Max             : {annotated_per_case.min()} / {annotated_per_case.max()}")

# =========================================================
# 2) TOPLAM DICOM KESİT SAYISI (dosya sisteminden)
#    Her vaka klasöründeki .dcm dosya sayısı. Medyan + maks.
# =========================================================
print("\n" + "=" * 60)
print("Vaka başına TOPLAM DICOM kesit sayısı (dosya sistemi)")
print("=" * 60)

for label, root in DIRS.items():
    # Her vaka klasöründeki .dcm sayısını topla
    counts = []
    for case_dir in sorted(root.iterdir()):
        if case_dir.is_dir():
            n_dcm = sum(1 for f in case_dir.iterdir() if f.suffix.lower() == ".dcm")
            counts.append(n_dcm)

    s = pd.Series(counts)
    print(f"\n--- {label} ({root.name}) ---")
    print(f"  Vaka sayısı          : {len(s)}")
    print(f"  Toplam DICOM kesit   : {s.sum():,}")
    print(f"  Medyan (kesit/vaka)  : {int(s.median())}")
    print(f"  Ortalama             : {s.mean():.1f}")
    print(f"  Maksimum (kesit/vaka): {s.max()}")
    print(f"  Minimum              : {s.min()}")
