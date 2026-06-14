"""
Weakly Supervised 3D Disease Localization

BB annotasyonları (2D, kesit bazlı) + TotalSegmentator organ maskeleri (3D)
→ Hastalığın 3D lokalizasyonu (weakly supervised, pseudo-label değil)

Yöntem:
  1. TotalSegmentator inference → anatomik organ maskeleri (sadece inference)
  2. Her hastalık sınıfı için ilgili organı seç
  3. BB annotasyonlu kesitlerde : BB_bölgesi ∩ organ_maskesi
  4. Boundary Slice z-aralığındaki diğer kesitlerde : organ_maskesi
  5. Z-aralığı dışında : background (0)
  Çıktı: çok-sınıflı 3D NIfTI  (0=bg, 1..6=hastalık sınıfı)
"""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import SimpleITK as sitk
except Exception:                      # pragma: no cover
    sitk = None

from .config import (SPLIT_DIR, RAW_TRAIN_DIR, RAW_TEST_DIR,
                     SEG_DATA_DIR, SUPER_CLASSES, DEFAULT_SEG)
from .dicom_utils import load_series, load_series_ids
from .segmentation import _dicom_to_nifti

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------
# Hastalık üst sınıfı → ilgili anatomik organ adı
DISEASE_TO_ORGAN: Dict[int, str] = {
    0: "Gall bladder",      # acute_cholecystitis
    1: "Kidney-Bladder",    # kidney_ureter_stone
    2: "Pancreas",          # acute_pancreatitis
    3: "Abdominal Aorta",   # aortic_aneurysm_dissection
    4: "appendix",          # acute_appendicitis (colon cecum yaklaşımı)
    5: "Colon",             # acute_diverticulitis
}

# Organ → TotalSegmentator NIfTI dosya adları (tek organ → birden fazla dosya olabilir)
TS_FILES_FOR_ORGAN: Dict[str, List[str]] = {
    "Abdominal Aorta": ["aorta"],
    "Gall bladder":    ["gallbladder"],
    "Pancreas":        ["pancreas"],
    "Kidney-Bladder":  ["kidney_left", "kidney_right", "urinary_bladder"],
    "Colon":           ["colon"],
    "appendix":        ["colon"],   # apendiks TotalSegmentator'da yok; kolon kullanılıyor
}

OUT_DIR = SEG_DATA_DIR / "weak_disease_masks"


# ---------------------------------------------------------------------------
# Cihaz seçimi (MPS > CUDA > CPU)
# ---------------------------------------------------------------------------
def _best_device() -> str:
    """Kullanılabilir en hızlı cihazı döndürür."""
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "gpu"
    except Exception:
        pass
    return "cpu"


# TotalSegmentator'da kullandığımız 6 organ → sadece bunlar segmente edilir
_TS_ROI_SUBSET: List[str] = [
    "aorta",
    "gallbladder",
    "pancreas",
    "colon",
    "kidney_left",
    "kidney_right",
    "urinary_bladder",
]


# ---------------------------------------------------------------------------
# TotalSegmentator Python API — CLI subprocess kullanmaz (requests çakışmasını atlar)
# ---------------------------------------------------------------------------
def _run_totalseg(input_nii: Path, out_dir: Path, fast: bool = True,
                  device: Optional[str] = None) -> None:
    """
    TotalSegmentator Python API ile sadece ihtiyaç duyulan 7 organı segment eder.

    Optimizasyonlar:
      • roi_subset → 104 yerine 7 organ  (~5-10x hız artışı)
      • device="mps" → Apple Silicon GPU  (~2-3x hız artışı)
    """
    from totalsegmentator.python_api import totalsegmentator as _ts
    out_dir.mkdir(parents=True, exist_ok=True)
    dev = device or _best_device()
    _ts(str(input_nii), str(out_dir),
        task="total",
        fast=fast,
        roi_subset=_TS_ROI_SUBSET,
        device=dev,
        quiet=True,
        verbose=False)


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------
def _load_organ_mask(ts_dir: Path, organ_name: str,
                     shape_zyx: Tuple[int, ...]) -> np.ndarray:
    """TotalSegmentator çıktısından organ binary maskesi döndürür."""
    merged = np.zeros(shape_zyx, dtype=np.uint8)
    for fname in TS_FILES_FOR_ORGAN.get(organ_name, []):
        p = ts_dir / f"{fname}.nii.gz"
        if p.exists():
            arr = sitk.GetArrayFromImage(sitk.ReadImage(str(p)))
            merged = np.maximum(merged, (arr > 0).astype(np.uint8))
    return merged


def _parse_annotations(case_rows: pd.DataFrame,
                        image_ids: List[int]
                        ) -> Tuple[Dict[int, List], Dict[str, Tuple[int, int]]]:
    """
    Manifest satırlarından BB ve Boundary Slice bilgisini çıkarır.

    Returns:
        bb_by_disease  : {super_id: [(z_idx, x1, y1, x2, y2), ...]}
        boundary_zrange: {organ_name: (z_lo, z_hi)}
    """
    idx_of = {img_id: i for i, img_id in enumerate(image_ids)}

    bb_by_disease: Dict[int, List] = {}
    boundary_z_lists: Dict[str, List[int]] = {}

    for _, row in case_rows.iterrows():
        z = idx_of.get(int(row["image_id"]))
        if z is None:
            continue

        # BB annotasyonları: "sid,x1,y1,x2,y2|..."
        for entry in str(row.get("bboxes", "") or "").split("|"):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split(",")
            if len(parts) != 5:
                continue
            sid, x1, y1, x2, y2 = map(int, parts)
            bb_by_disease.setdefault(sid, []).append((z, x1, y1, x2, y2))

        # Boundary Slice annotasyonları
        for org in str(row.get("anatomical_boundary", "") or "").split(";"):
            org = org.strip()
            if org and org.lower() != "nan":
                boundary_z_lists.setdefault(org, []).append(z)

    boundary_zrange = {
        org: (min(zs), max(zs)) for org, zs in boundary_z_lists.items()
    }
    return bb_by_disease, boundary_zrange


def _make_disease_mask(bb_by_disease: Dict[int, List],
                       boundary_zrange: Dict[str, Tuple[int, int]],
                       ts_dir: Path,
                       shape_zyx: Tuple[int, ...]) -> np.ndarray:
    """
    BB + organ maskesi → çok-sınıflı 3D hastalık maskesi.

    Kural:
      • BB'li kesitler  : BB_bölgesi ∩ organ_maskesi
                          (örtüşme yoksa BB_bölgesi doğrudan kullanılır)
      • Arası kesitler  : organ_maskesi  (boundary z-aralığı içinde)
      • Dışı            : 0 (background)
    """
    out = np.zeros(shape_zyx, dtype=np.uint8)

    for disease_id, bb_list in bb_by_disease.items():
        organ_name = DISEASE_TO_ORGAN.get(disease_id)
        if organ_name is None:
            continue

        organ_mask = _load_organ_mask(ts_dir, organ_name, shape_zyx)

        # Boundary z-aralığı — yoksa BB'nin kapsamına genişlet
        if organ_name in boundary_zrange:
            z_lo, z_hi = boundary_zrange[organ_name]
        else:
            zs = [z for z, *_ in bb_list]
            margin = max(5, len(zs))
            z_lo = max(0, min(zs) - margin)
            z_hi = min(shape_zyx[0] - 1, max(zs) + margin)

        label = disease_id + 1  # 1-indexed (0 = background)

        # 1) BB annotasyonlu kesitler
        bb_z_set: set = set()
        for z, x1, y1, x2, y2 in bb_list:
            if not (0 <= z < shape_zyx[0]):
                continue
            roi = np.zeros(shape_zyx[1:], dtype=np.uint8)
            roi[y1:y2, x1:x2] = 1
            hit = organ_mask[z] & roi
            out[z][hit > 0 if hit.sum() > 0 else roi > 0] = label
            bb_z_set.add(z)

        # 2) Boundary z-aralığındaki diğer kesitler: organ maskesi
        for z in range(z_lo, z_hi + 1):
            if z not in bb_z_set:
                out[z][organ_mask[z] > 0] = label

    return out


# ---------------------------------------------------------------------------
# Ana pipeline
# ---------------------------------------------------------------------------
def generate_weak_masks(limit: Optional[int] = None,
                        out_dir: Path = OUT_DIR,
                        totalseg_fast: bool = True,
                        device: Optional[str] = None,
                        n_dicom_workers: int = 4) -> None:
    """
    BB annotasyonu olan her vaka için weakly supervised 3D hastalık maskesi üretir.

    Optimizasyonlar:
      • DICOM→NIfTI paralel dönüşüm (I/O bound, ThreadPoolExecutor)
      • TotalSegmentator: sadece 7 organ (roi_subset), MPS/GPU cihaz
      • TotalSegmentator sıralı çalışır (zaten tüm çekirdekleri kullanır)

    Args:
        limit           : Debug için kaç vaka işlensin (None = hepsi)
        out_dir         : NIfTI maskelerinin yazılacağı klasör
        totalseg_fast   : TotalSegmentator fast modu
        device          : "mps"|"gpu"|"cpu"|None (None=otomatik seç)
        n_dicom_workers : Paralel DICOM→NIfTI worker sayısı
    """
    if sitk is None:
        raise RuntimeError("SimpleITK gerekli: pip install SimpleITK")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ts").mkdir(exist_ok=True)

    dev = device or _best_device()
    print(f"Cihaz: {dev}")

    manifest = pd.read_csv(SPLIT_DIR / "manifest.csv")

    # Sadece BB annotasyonu olan vakalar
    bb_cases = manifest[manifest["bboxes"].fillna("") != ""]["case"].unique()
    case_ids = sorted(bb_cases.tolist())
    if limit is not None:
        case_ids = case_ids[:limit]

    # Vaka → DICOM dizini eşlemesi
    case_dirs: Dict[int, Path] = {}
    for cid in case_ids:
        d = next(
            (b / str(cid) for b in (RAW_TRAIN_DIR, RAW_TEST_DIR)
             if (b / str(cid)).is_dir()),
            None,
        )
        if d:
            case_dirs[cid] = d

    missing = set(case_ids) - set(case_dirs)
    if missing:
        print(f"  [uyarı] {len(missing)} vaka dizini bulunamadı, atlanıyor.")

    todo = [cid for cid in case_ids if cid in case_dirs
            and not (out_dir / f"ABE_{cid:05d}_disease.nii.gz").exists()]

    print(f"BB annotasyonlu vaka: {len(case_ids)}  |  işlenecek: {len(todo)}")

    # ── Adım 1: Paralel DICOM → NIfTI (I/O bound) ────────────────────────
    def _convert(cid: int) -> tuple:
        nii = out_dir / f"ABE_{cid:05d}_0000.nii.gz"
        if nii.exists():
            return cid, None
        try:
            _dicom_to_nifti(case_dirs[cid], nii)
            return cid, None
        except Exception as e:
            return cid, str(e)

    workers = min(n_dicom_workers, os.cpu_count() or 4)
    print(f"DICOM→NIfTI paralel dönüşüm ({workers} worker)...")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for cid, err in tqdm(ex.map(_convert, todo),
                              total=len(todo), desc="DICOM→NIfTI"):
            if err:
                print(f"  [skip dicom] case {cid}: {err}")

    # ── Adım 2: TotalSegmentator + maske üretimi (sıralı) ────────────────
    skipped, done = 0, 0
    for case_id in tqdm(todo, desc="TotalSeg+Maske"):
        out_path = out_dir / f"ABE_{case_id:05d}_disease.nii.gz"
        nii_path = out_dir / f"ABE_{case_id:05d}_0000.nii.gz"

        if not nii_path.exists():
            skipped += 1
            continue

        try:
            ref       = sitk.ReadImage(str(nii_path))
            shape_zyx = sitk.GetArrayFromImage(ref).shape

            # TotalSegmentator inference — başarısız olursa BB-only moda geç
            ts_dir = out_dir / "ts" / str(case_id)
            ts_dir.mkdir(parents=True, exist_ok=True)
            if not any(ts_dir.glob("*.nii.gz")):
                try:
                    _run_totalseg(nii_path, ts_dir, fast=totalseg_fast, device=dev)
                except Exception as ts_exc:
                    # TotalSegmentator yoksa veya başarısızsa BB-only modda devam et.
                    # _load_organ_mask() zaten eksik dosyalar için sıfır maske döner;
                    # BB kesitlerinde mevcut fallback (roi doğrudan) devreye girer.
                    print(f"  [uyari] TotalSeg hatasi, BB-only mod: {ts_exc}")

            # Annotasyonları çözümle — piksel yüklemeye gerek yok, sadece z-sıralı id'ler
            image_ids     = load_series_ids(case_dirs[case_id])
            case_rows     = manifest[manifest["case"] == case_id]
            bb_by_dis, bz = _parse_annotations(case_rows, image_ids)

            if not bb_by_dis:
                skipped += 1
                continue

            # 3D hastalık maskesi
            mask = _make_disease_mask(bb_by_dis, bz, ts_dir, shape_zyx)

            # Kaydet
            out_img = sitk.GetImageFromArray(mask)
            out_img.CopyInformation(ref)
            sitk.WriteImage(out_img, str(out_path))

            # Geçici NIfTI sil (disk tasarrufu)
            nii_path.unlink(missing_ok=True)
            done += 1

        except Exception as exc:
            print(f"  [skip] case {case_id}: {exc}")
            skipped += 1

    _write_stats(case_ids, out_dir)
    print(f"\nBitti — işlenen: {done}, atlanan: {skipped}")
    print(f"Maskeler: {out_dir}")


def _write_stats(case_ids: List[int], out_dir: Path) -> None:
    """Sınıf başına toplam voxel sayısını JSON olarak kaydeder."""
    counts: Dict[int, int] = {i + 1: 0 for i in range(len(SUPER_CLASSES))}
    for p in out_dir.glob("*_disease.nii.gz"):
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(p)))
        for cls_id in counts:
            counts[cls_id] += int((arr == cls_id).sum())

    stats = {
        "processed_cases": len(case_ids),
        "voxel_counts": {
            SUPER_CLASSES[i]: counts[i + 1]
            for i in range(len(SUPER_CLASSES))
        },
    }
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2))
    print("\nSınıf voxel sayıları:")
    for cls, n in stats["voxel_counts"].items():
        print(f"  {cls:35s}: {n:,}")
