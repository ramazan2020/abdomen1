"""
DICOM yükleme, HU dönüşümü, pencereleme ve yeniden örnekleme yardımcıları.

Tüm görüntü yükleme işlemleri buradan geçmelidir; böylece ön işleme tek noktadan
değiştirilebilir ve tekrar üretilebilirlik korunur.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
import pydicom
from pydicom.dataset import FileDataset

try:
    import SimpleITK as sitk
except Exception:                       # pragma: no cover
    sitk = None

from .config import DEFAULT_WINDOWS, Window, TARGET_SPACING_XYZ


# ---------------------------------------------------------------------------
# SLICE SEVİYESİ (2D)
# ---------------------------------------------------------------------------
def read_dicom(path: Path) -> FileDataset:
    """pydicom wrapper — InvalidDICOM hatalarını hızlı yakalamak için."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*excess padding.*", category=UserWarning)
        warnings.filterwarnings("ignore", message=".*DICOM File Meta.*", category=UserWarning)
        return pydicom.dcmread(str(path), force=True)


def dicom_to_hu(ds: FileDataset) -> np.ndarray:
    """Ham piksel değerini Hounsfield Unit'e çevirir."""
    arr = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1.0) or 1.0)
    intercept = float(getattr(ds, "RescaleIntercept", 0.0) or 0.0)
    hu = arr * slope + intercept
    # Bazı cihazlarda tanımsız pikseller -2000 veya -3024 ile işaretlenir
    hu[hu < -1024] = -1024
    hu[hu > 3071] = 3071
    return hu


def window_hu(hu: np.ndarray, win: Window) -> np.ndarray:
    """HU dizisini [0,1] aralığında pencereler."""
    low = win.level - win.width / 2
    high = win.level + win.width / 2
    out = (hu - low) / max(high - low, 1e-6)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def hu_to_three_channel(hu: np.ndarray,
                        windows: Sequence[Window] = DEFAULT_WINDOWS) -> np.ndarray:
    """HxW HU → HxWx3 pencerelenmiş float32 ∈ [0,1]."""
    chans = [window_hu(hu, w) for w in windows]
    return np.stack(chans, axis=-1)


# ---------------------------------------------------------------------------
# SERİ (3D) SEVİYESİ
# ---------------------------------------------------------------------------
@dataclass
class CTSeries:
    """Bir vakaya ait tüm DICOM kesitlerini bellekte 3B olarak tutar."""
    case_id: str
    image_ids: List[int]        # kesitlerin Image Id'si (Bilgi.xlsx ile eşleşen)
    hu: np.ndarray              # (Z, Y, X) HU
    spacing_zyx: Tuple[float, float, float]
    sort_key: str               # "ImagePositionPatient.z" | "InstanceNumber"


def _sort_dicoms(paths: List[Path]) -> Tuple[List[FileDataset], str]:
    """Kesitleri önce ImagePositionPatient.z, yoksa InstanceNumber ile sıralar."""
    datasets = [read_dicom(p) for p in paths]
    if all(hasattr(d, "ImagePositionPatient") for d in datasets):
        datasets.sort(key=lambda d: float(d.ImagePositionPatient[2]))
        return datasets, "ImagePositionPatient.z"
    datasets.sort(key=lambda d: int(getattr(d, "InstanceNumber", 0) or 0))
    return datasets, "InstanceNumber"


def load_series(case_dir: Path) -> CTSeries:
    """Bir vaka klasöründeki tüm .dcm dosyalarını okuyup 3B volüm üretir."""
    dcm_paths = sorted(p for p in case_dir.iterdir() if p.suffix.lower() == ".dcm")
    if not dcm_paths:
        raise FileNotFoundError(f"DICOM bulunamadı: {case_dir}")
    datasets, key = _sort_dicoms(dcm_paths)

    hu_volume = np.stack([dicom_to_hu(d) for d in datasets], axis=0)

    # Spacing (z, y, x)
    y_sp, x_sp = map(float, datasets[0].PixelSpacing)
    if len(datasets) >= 2 and hasattr(datasets[0], "ImagePositionPatient"):
        z_sp = float(abs(datasets[1].ImagePositionPatient[2]
                         - datasets[0].ImagePositionPatient[2]))
    else:
        z_sp = float(getattr(datasets[0], "SliceThickness", 1.0) or 1.0)

    image_ids = [int(Path(dcm_paths[i]).stem) for i, _ in enumerate(datasets)]

    return CTSeries(
        case_id=case_dir.name,
        image_ids=image_ids,
        hu=hu_volume.astype(np.float32),
        spacing_zyx=(z_sp, y_sp, x_sp),
        sort_key=key,
    )


# ---------------------------------------------------------------------------
# YENİDEN ÖRNEKLEME (3D)
# ---------------------------------------------------------------------------
def resample_volume(volume_zyx: np.ndarray,
                    src_spacing_zyx: Sequence[float],
                    dst_spacing_xyz: Sequence[float] = TARGET_SPACING_XYZ,
                    is_label: bool = False) -> Tuple[np.ndarray, Tuple[float, float, float]]:
    """
    SimpleITK tabanlı izotropik/anizotropik yeniden örnekleme.
    is_label=True → NearestNeighbor interpolasyonu (segmentasyon maskeleri için).
    """
    if sitk is None:
        raise RuntimeError("SimpleITK yüklü değil; `pip install SimpleITK` gerekir.")

    img = sitk.GetImageFromArray(volume_zyx)
    # SimpleITK spacing = (x, y, z)
    img.SetSpacing((float(src_spacing_zyx[2]),
                    float(src_spacing_zyx[1]),
                    float(src_spacing_zyx[0])))

    dst_sp_xyz = tuple(map(float, dst_spacing_xyz))
    src_size_xyz = img.GetSize()
    src_sp_xyz = img.GetSpacing()
    dst_size_xyz = tuple(
        int(round(src_size_xyz[i] * src_sp_xyz[i] / dst_sp_xyz[i])) for i in range(3)
    )

    interp = sitk.sitkNearestNeighbor if is_label else sitk.sitkBSpline
    out = sitk.Resample(
        img, dst_size_xyz, sitk.Transform(), interp,
        img.GetOrigin(), dst_sp_xyz, img.GetDirection(),
        0.0, img.GetPixelID(),
    )
    out_np = sitk.GetArrayFromImage(out)   # (z, y, x)
    dst_sp_zyx = (dst_sp_xyz[2], dst_sp_xyz[1], dst_sp_xyz[0])
    return out_np, dst_sp_zyx


# ---------------------------------------------------------------------------
# BOUNDING BOX
# ---------------------------------------------------------------------------
def parse_bbox(raw: str) -> Tuple[int, int, int, int] | None:
    """`x1,y1-x2,y2` → (x1, y1, x2, y2). Hatalı ise None."""
    try:
        a, b = raw.split("-")
        x1, y1 = (int(v) for v in a.split(","))
        x2, y2 = (int(v) for v in b.split(","))
        if x2 <= x1 or y2 <= y1:
            return None
        return x1, y1, x2, y2
    except Exception:
        return None


def bbox_xyxy_to_yolo(bbox: Tuple[int, int, int, int],
                      img_h: int, img_w: int) -> Tuple[float, float, float, float]:
    """(x1,y1,x2,y2) piksel → (cx, cy, w, h) normalize."""
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2.0 / img_w
    cy = (y1 + y2) / 2.0 / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return cx, cy, w, h
