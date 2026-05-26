"""
Projedeki tüm yolları, sınıf haritasını, pencere ayarlarını ve varsayılanları
tek noktadan yönetir. Tüm komut dosyaları buradan import eder.

Colab / uzak ortam için ABDOMEN_* ortam değişkenleriyle yollar override edilebilir.
Alt süreçler (ProcessPoolExecutor) de bu değişkenleri miras alır.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

_env = os.environ.get  # kısa takma ad

# ---------------------------------------------------------------------------
# YOLLAR
# ---------------------------------------------------------------------------
ROOT      = Path(_env("ABDOMEN_PROJECT_ROOT", str(Path(__file__).resolve().parents[1])))
DATA_ROOT = Path(_env("ABDOMEN_DATA_ROOT",    str(ROOT)))
RAW_TRAIN_DIR = Path(_env("ABDOMEN_TRAIN_DIR",  str(DATA_ROOT / "Egitim Verisi")))
RAW_TEST_DIR  = Path(_env("ABDOMEN_TEST_DIR",   str(DATA_ROOT / "Test Verisi")))
BILGI_XLSX    = Path(_env("ABDOMEN_BILGI_XLSX", str(DATA_ROOT / "Bilgi.xlsx")))

# çıktılar
OUT_DIR      = Path(_env("ABDOMEN_OUT_DIR",      str(ROOT / "outputs")))
SPLIT_DIR    = Path(_env("ABDOMEN_SPLIT_DIR",    str(OUT_DIR / "splits")))
CLS_DATA_DIR = Path(_env("ABDOMEN_CLS_DATA_DIR", str(OUT_DIR / "cls_data")))
DET_DATA_DIR = Path(_env("ABDOMEN_DET_DATA_DIR", str(OUT_DIR / "det_data")))
SEG_DATA_DIR = Path(_env("ABDOMEN_SEG_DATA_DIR", str(OUT_DIR / "seg_data")))
CKPT_DIR     = Path(_env("ABDOMEN_CKPT_DIR",     str(OUT_DIR / "checkpoints")))
LOG_DIR      = Path(_env("ABDOMEN_LOG_DIR",      str(OUT_DIR / "logs")))
for d in (OUT_DIR, SPLIT_DIR, CLS_DATA_DIR, DET_DATA_DIR, SEG_DATA_DIR, CKPT_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# SINIF HARİTASI (16 ham → 6 üst sınıf)
# ---------------------------------------------------------------------------
# Makaledeki 6 üst sınıfı hedefliyoruz. Hem BB (patoloji) hem Boundary Slice
# (anatomik) etiketleri bu harita ile çözümlenir.

SUPER_CLASSES: List[str] = [
    "acute_cholecystitis",        # 0
    "kidney_ureter_stone",        # 1
    "acute_pancreatitis",         # 2
    "aortic_aneurysm_dissection", # 3
    "acute_appendicitis",         # 4
    "acute_diverticulitis",       # 5
]

# Ham etiket → üst sınıf ID (patoloji etiketleri)
RAW_PATHOLOGY_TO_SUPER: Dict[str, int] = {
    "Compatible with acute cholecystitis": 0,
    "Gallbladder stone": 0,                 # safra taşı, kolesistit kümesine
    "Kidney stone": 1,
    "ureteral stone": 1,
    "Compatible with acute pancreatitis": 2,
    "Abdominal aortic aneurysm": 3,
    "Abdominal aortic dissection": 3,
    "Compatible with acute appendicitis": 4,
    "Compatible with acute diverticulitis": 5,
    "Calcified diverticulum": 5,
}

# Anatomik (Boundary Slice) sınıfları — segmentasyon için
ANATOMICAL_CLASSES: List[str] = [
    "Abdominal Aorta",
    "Gall bladder",
    "Pancreas",
    "Kidney-Bladder",
    "Colon",
    "appendix",
]
ANATOMICAL_TO_ID: Dict[str, int] = {c: i + 1 for i, c in enumerate(ANATOMICAL_CLASSES)}
# id 0 = background

# ---------------------------------------------------------------------------
# DICOM / HU PENCERELERİ
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Window:
    name: str
    level: float        # WL / center
    width: float        # WW

# Üç kanallı girdi için varsayılan set
DEFAULT_WINDOWS: Tuple[Window, Window, Window] = (
    Window("soft_tissue", level=40,  width=400),   # yumuşak doku  – WL=40 WW=400
    Window("liver",       level=30,  width=150),   # karaciğer     – WL=30 WW=150
    Window("calcified",   level=450, width=1500),  # kalsifiye yapı– WL=450 WW=1500
)
# DEFAULT_WINDOWS: Tuple[Window, Window, Window] = (
#     Window("soft_tissue", level=50,  width=400),   # yumuşak doku  – WL=50 WW=400
#     Window("liver",       level=30,  width=150),   # karaciğer     – WL=30 WW=150
#     Window("calcified",   level=400, width=2000),  # kalsifiye yapı– WL=400 WW=2000
# )

# Yeniden örnekleme hedefi (anizotropik — abdomen CT için standart)
TARGET_SPACING_XYZ: Tuple[float, float, float] = (0.8, 0.8, 2.5)
TARGET_MATRIX: int = 512

# ---------------------------------------------------------------------------
# EĞİTİM / DOĞRULAMA
# ---------------------------------------------------------------------------
@dataclass
class SplitConfig:
    n_splits: int = 5
    seed: int = 42
    holdout_frac: float = 0.15        # yayın raporu için hold-out
    stratify_on_super: bool = True    # her fold'da üst sınıf dengesi hedeflenir


@dataclass
class ClsConfig:
    backbone: str = "convnext_base.fb_in22k_ft_in1k"
    num_classes: int = 6
    input_size: int = 384
    batch_size: int = 48   # M5 unified memory için artırıldı (eski: 32)
    epochs: int = 50
    lr: float = 2e-4
    weight_decay: float = 1e-4
    warmup_epochs: int = 3
    use_focal: bool = True
    focal_gamma: float = 2.0
    mixup_alpha: float = 0.2
    accum_steps: int = 1
    precision: str = "bf16-mixed"


@dataclass
class DetConfig:
    model: str = "yolov8m.pt"   # yolov8x → m (overfitting azaltır)
    img_size: int = 512
    batch_size: int = 16
    epochs: int = 100
    mosaic: float = 0.0         # CT'de anlamsız, devre dışı
    mixup: float = 0.0          # CT'de anlamsız, devre dışı
    workers_mps: int = 2
    workers_cuda: int = 8
    workers_cpu: int = 4
    patience: int = 30
    lr0: float = 0.001          # CT ince yapılar için düşük LR
    lrf: float = 0.01           # final LR = lr0 * lrf
    weight_decay: float = 0.0005
    fliplr: float = 0.0         # anatomi simetrisi yok (appendix, safra kesesi)
    flipud: float = 0.0
    hsv_h: float = 0.0          # CT grayscale, HSV anlamsız
    hsv_s: float = 0.0
    hsv_v: float = 0.4          # parlaklık hafif değişim — HU pencerelemeyle uyumlu


@dataclass
class SegConfig:
    target_spacing: Tuple[float, float, float] = TARGET_SPACING_XYZ
    patch_size: Tuple[int, int, int] = (192, 192, 96)
    totalseg_task: str = "total"     # TotalSegmentator preset
    num_classes: int = len(ANATOMICAL_CLASSES) + 1  # +background
    pseudo_iterations: int = 2       # self-training kaç tur

DEFAULT_SPLIT = SplitConfig()
DEFAULT_CLS = ClsConfig()
DEFAULT_DET = DetConfig()
DEFAULT_SEG = SegConfig()


# ---------------------------------------------------------------------------
# YARDIMCI
# ---------------------------------------------------------------------------
def super_id_from_raw(raw_class: str) -> int | None:
    """Ham etiket adını 6 üst sınıfa eşler; anatomik etiket ise None döner."""
    return RAW_PATHOLOGY_TO_SUPER.get(raw_class)


def ensure_exists(path: Path, kind: str = "path") -> Path:
    if not path.exists():
        raise FileNotFoundError(f"{kind} bulunamadı: {path}")
    return path
