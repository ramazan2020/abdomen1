"""
Bounding Box boyut dağılımı — çok panelli görselleştirme.
  1) sqrt(area) histogramı (eğitim + yarışma üst üste)
  2) Sınıfa göre sqrt(area) boxplot'u
  3) Genişlik vs yükseklik scatter (log ölçekli)
  4) Log10 alan (piksel²) histogramı
"""
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---- VERİYİ YÜKLE ----
BASE = Path(os.environ.get(
    "TR_ABDOMEN_BASE",
    r"/Users/ramazanpolat/Desktop/datasets/abdomen"
))

OUT = BASE / "Analiz_Sonuclari" / "grafikler" / "bb_boyut_dagilimi.png"
sheets = pd.read_excel(BASE / "Bilgi.xlsx", sheet_name=None)


def parse_bbox(s: str):
    """`x1,y1-x2,y2` → (x1,y1,x2,y2). Hatalı ise None."""
    try:
        a, b = s.split("-")
        x1, y1 = map(int, a.split(","))
        x2, y2 = map(int, b.split(","))
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2
    except Exception:
        return None


def bbox_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Bounding Box satırlarından w, h, area sütunlarını üretir."""
    bb = df[df["Type"] == "Bounding Box"].copy()
    parsed = bb["Data"].apply(parse_bbox)
    mask = parsed.notna()
    bb = bb.loc[mask].copy()
    xyxy = np.array([list(p) for p in parsed[mask]])
    bb["w"] = xyxy[:, 2] - xyxy[:, 0]
    bb["h"] = xyxy[:, 3] - xyxy[:, 1]
    bb["area"] = bb["w"] * bb["h"]
    bb["sqrt_area"] = np.sqrt(bb["area"])
    return bb


train_bb = bbox_frame(sheets["TRAIININGDATA"])
comp_bb = bbox_frame(sheets["COMPETITIONDATA"])
print(f"Eğitim BB sayısı: {len(train_bb):,}")
print(f"Yarışma BB sayısı: {len(comp_bb):,}")

# ---- ÇİZİM ----
plt.rcParams["font.family"] = "DejaVu Sans"
fig, axes = plt.subplots(2, 2, figsize=(13, 10))

# (1) Üst üste histogram: sqrt(area)
ax = axes[0, 0]
bins = np.linspace(0, 250, 60)
ax.hist(train_bb["sqrt_area"], bins=bins, alpha=0.55,
        color="#1f77b4", label=f"Eğitim (n={len(train_bb):,})")
ax.hist(comp_bb["sqrt_area"], bins=bins, alpha=0.55,
        color="#ff7f0e", label=f"Yarışma (n={len(comp_bb):,})")
ax.axvline(train_bb["sqrt_area"].median(), color="#1f77b4",
           linestyle="--", label=f"Eğitim medyan={train_bb['sqrt_area'].median():.0f}")
ax.axvline(comp_bb["sqrt_area"].median(), color="#ff7f0e",
           linestyle="--", label=f"Yarışma medyan={comp_bb['sqrt_area'].median():.0f}")
ax.set_xlabel("√alan (piksel)")
ax.set_ylabel("BB sayısı")
ax.set_title("(a) BB boyut (√alan) histogramı")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

# (2) Sınıfa göre boxplot (eğitim seti)
ax = axes[0, 1]
order = train_bb.groupby("Class")["sqrt_area"].median().sort_values().index.tolist()
data = [train_bb.loc[train_bb["Class"] == c, "sqrt_area"].values for c in order]
bp = ax.boxplot(data, vert=False, labels=order, showfliers=False,
                patch_artist=True)
for patch in bp["boxes"]:
    patch.set_facecolor("#4c72b0")
    patch.set_alpha(0.7)
ax.set_xlabel("√alan (piksel)")
ax.set_title("(b) Eğitim – Sınıfa göre BB boyutu")
ax.grid(alpha=0.3, axis="x")

# (3) Width vs Height scatter (log ölçek)
ax = axes[1, 0]
ax.scatter(train_bb["w"], train_bb["h"], s=3, alpha=0.15,
           color="#1f77b4", label="Eğitim")
ax.scatter(comp_bb["w"], comp_bb["h"], s=3, alpha=0.15,
           color="#ff7f0e", label="Yarışma")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("genişlik (px, log)")
ax.set_ylabel("yükseklik (px, log)")
ax.set_title("(c) Genişlik vs. Yükseklik")
ax.plot([1, 512], [1, 512], "k--", alpha=0.4, label="kare (w=h)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3, which="both")

# (4) Log10 alan histogramı
ax = axes[1, 1]
bins = np.linspace(1, 5, 50)                  # 10 px² ... 100k px²
ax.hist(np.log10(train_bb["area"]), bins=bins, alpha=0.55,
        color="#1f77b4", label="Eğitim")
ax.hist(np.log10(comp_bb["area"]), bins=bins, alpha=0.55,
        color="#ff7f0e", label="Yarışma")
ax.set_xlabel("log₁₀(alan) (piksel²)")
ax.set_ylabel("BB sayısı")
ax.set_title("(d) BB alanı (log ölçek)")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)

plt.suptitle("TR_ABDOMEN_RAD_EMERGENCY — Bounding Box Boyut Dağılımı",
             fontsize=14, fontweight="bold")
plt.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUT, dpi=140, bbox_inches="tight")
plt.close()

print(f"\nGrafik kaydedildi: {OUT}")

# ---- SAYISAL ÖZET ----
print("\n" + "=" * 60)
print("Sınıf bazında medyan √alan (piksel) — Eğitim")
print("=" * 60)
summary = (train_bb.groupby("Class")
           .agg(count=("area", "size"),
                median_w=("w", "median"),
                median_h=("h", "median"),
                median_sqrt_area=("sqrt_area", "median"))
           .round(1)
           .sort_values("median_sqrt_area"))
print(summary.to_string())
