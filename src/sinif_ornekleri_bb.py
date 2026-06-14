"""
Sınıf başına örnek CT kesiti + Bounding Box overlay.

- Bilgi.xlsx'teki Bounding Box annotasyonlarından her patoloji sınıfı için
  temsili bir örnek seçer (medyan sıralı orta örnek).
- DICOM'u okur, HU'ya çevirir, abdomen penceresi uygular.
- BB'yi kırmızı dikdörtgen olarak üstüne çizer.
- 10 sınıf için 2x5 grid çıkarır.
"""
import os
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydicom

# ---- VERİYİ YÜKLE ----
BASE = Path(os.environ.get(
    "TR_ABDOMEN_BASE",
    r"/Users/ramazanpolat/Desktop/datasets/abdomenDataSet"
))

    
TRAIN_DIR = BASE / "Egitim Verisi"
TEST_DIR = BASE / "Test Verisi"
OUT = BASE / "Analiz_Sonuclari" / "grafikler" / "sinif_ornekleri_bb.png"

# Gösterilecek 10 patoloji sınıfı (eğitim setindeki tüm BB sınıfları)
CLASSES = [
    "Abdominal aortic aneurysm",
    "Abdominal aortic dissection",
    "Compatible with acute pancreatitis",
    "Compatible with acute cholecystitis",
    "Compatible with acute appendicitis",
    "Compatible with acute diverticulitis",
    "Calcified diverticulum",
    "Kidney stone",
    "ureteral stone",
    "Gallbladder stone",
]

# ---- YARDIMCI FONKSİYONLAR ----
def parse_bbox(s):
    a, b = s.split("-")
    x1, y1 = map(int, a.split(","))
    x2, y2 = map(int, b.split(","))
    return x1, y1, x2, y2


def load_hu(dcm_path: Path) -> np.ndarray:
    """DICOM → HU dizisi (RescaleSlope/Intercept uygulanır)."""
    ds = pydicom.dcmread(str(dcm_path))
    arr = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
    return arr * slope + intercept


def window(hu: np.ndarray, level: float = 40, width: float = 400) -> np.ndarray:
    """Pencereleme: [0,1] aralığına normalize eder."""
    lo, hi = level - width / 2, level + width / 2
    return np.clip((hu - lo) / (hi - lo), 0, 1)


def dicom_path_for(case: int, img: int) -> Path:
    """Case Number eğitim veya yarışma klasöründe olabilir."""
    for root in (TRAIN_DIR, TEST_DIR):
        p = root / str(case) / f"{img}.dcm"
        if p.exists():
            return p
    raise FileNotFoundError(f"{case}/{img}.dcm bulunamadı")


# ---- ÖRNEK SEÇİMİ ----
sheets = pd.read_excel(BASE / "Bilgi.xlsx", sheet_name=None)
# Eğitimde olmayanları yarışmadan al (ör. acute_appendicitis'te yarışmada daha çok var)
all_bb = pd.concat([sheets["TRAIININGDATA"], sheets["COMPETITIONDATA"]])
all_bb = all_bb[all_bb["Type"] == "Bounding Box"]

# ---- ÇİZİM ----
plt.rcParams["font.family"] = "DejaVu Sans"
fig, axes = plt.subplots(2, 5, figsize=(18, 8))
axes = axes.flatten()

for i, cls in enumerate(CLASSES):
    ax = axes[i]
    sub = all_bb[all_bb["Class"] == cls].reset_index(drop=True)
    if len(sub) == 0:
        ax.text(0.5, 0.5, f"{cls}\n(örnek yok)", ha="center", va="center")
        ax.axis("off")
        continue

    # Medyan alanlı BB'yi seç (aşırı küçük/büyük olmasın)
    sub = sub.assign(area=sub["Data"].apply(
        lambda s: (lambda b: (b[2]-b[0])*(b[3]-b[1]))(parse_bbox(s))))
    sub = sub.sort_values("area").reset_index(drop=True)
    row = sub.iloc[len(sub) // 2]        # medyan
    x1, y1, x2, y2 = parse_bbox(row["Data"])

    try:
        dpath = dicom_path_for(int(row["Case Number"]), int(row["Image Id"]))
        hu = load_hu(dpath)
        img = window(hu, level=40, width=400)   # abdomen penceresi
    except Exception as exc:
        ax.text(0.5, 0.5, f"{cls}\nhata: {exc}", ha="center", va="center",
                fontsize=8)
        ax.axis("off")
        continue

    ax.imshow(img, cmap="gray", vmin=0, vmax=1)
    rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                             linewidth=2.2, edgecolor="#ff1744",
                             facecolor="none")
    ax.add_patch(rect)
    # Etiket: sol-üst köşede kırmızı arka plan
    ax.text(x1, max(y1 - 6, 10), cls, fontsize=9, color="white",
            bbox=dict(facecolor="#ff1744", alpha=0.85, pad=2, edgecolor="none"))
    ax.set_title(f"vaka={row['Case Number']}  kesit={row['Image Id']}  "
                 f"alan={int(row['area'])} px²", fontsize=9)
    ax.axis("off")

plt.suptitle("TR_ABDOMEN_RAD_EMERGENCY — Sınıf Başına BB Overlay Örnekleri "
             "(W=400, L=40 abdomen penceresi)",
             fontsize=14, fontweight="bold", y=0.98)
plt.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Grafik kaydedildi: {OUT}")
