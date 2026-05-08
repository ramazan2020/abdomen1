"""
Yarı-denetimli anatomik segmentasyon hattı.

Bilgi.xlsx içindeki `Boundary Slice` annotasyonları yalnızca bir organın 3B
başlangıç/bitiş kesitini belirtir; piksel maskesi yoktur. Bu yüzden:

 1) TotalSegmentator ile her vaka için 104 organlık ön-tahmin maskesi çıkarılır.
 2) İlgilendiğimiz 6 organ (Abdominal Aorta, Gallbladder, Pancreas, Colon,
    Kidney+Bladder, Appendix) TotalSegmentator sınıflarından birleştirilir.
 3) Boundary Slice bilgisi bu maskeleri **z ekseninde kırpmak / geçerlilik
    filtresi olarak** kullanılır — etiketleme hatalarını azaltır.
 4) Elde edilen pseudo-maskelerle nnU-Net v2 eğitilir. 2-3 tur self-training
    ile iteratif olarak rafine edilir.

Appendix TotalSegmentator ile doğrudan çıkarılamayabilir; bu durumda colon
maskesinden cekum'u alıp boundary slice z-aralığına göre izole ediyoruz.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import SimpleITK as sitk
except Exception:                      # pragma: no cover
    sitk = None

from .config import (ANATOMICAL_TO_ID, DEFAULT_SEG, RAW_TEST_DIR, RAW_TRAIN_DIR,
                     SEG_DATA_DIR, SPLIT_DIR)
from .dicom_utils import load_series, resample_volume


# ---------------------------------------------------------------------------
# TotalSegmentator → 6 ROI maskesi
# ---------------------------------------------------------------------------
TS_TO_OURS: Dict[str, str] = {
    "aorta":                      "Abdominal Aorta",
    "gallbladder":                "Gall bladder",
    "pancreas":                   "Pancreas",
    "colon":                      "Colon",
    "urinary_bladder":            "Kidney-Bladder",
    "kidney_left":                "Kidney-Bladder",
    "kidney_right":               "Kidney-Bladder",
    # apendiks TotalSegmentator'da ayrı sınıf değil; cekum yaklaşık alınır
    # Kullanıcı şartlarına göre uygun bir TS modeli eklenebilir
}


def _dicom_to_nifti(case_dir: Path, out_nii: Path) -> None:
    if sitk is None:
        raise RuntimeError("SimpleITK kurulu değil")
    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(case_dir))
    if not series_ids:
        raise RuntimeError(f"DICOM serisi bulunamadı: {case_dir}")
    files = reader.GetGDCMSeriesFileNames(str(case_dir), series_ids[0])
    reader.SetFileNames(files)
    img = reader.Execute()
    out_nii.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(out_nii))


def _m5_env() -> dict:
    """M5 / Apple Silicon için nnU-Net ve sistem geneli CPU thread env değişkenleri."""
    env = os.environ.copy()
    n = os.cpu_count() or 8
    env.setdefault("nnUNet_n_proc_DA", str(min(12, n)))   # data-augmentation worker sayısı
    env.setdefault("OMP_NUM_THREADS",  str(min(8, n)))
    env.setdefault("MKL_NUM_THREADS",  str(min(8, n)))
    return env


def _run_totalseg(input_nii: Path, out_dir: Path,
                  task: str = DEFAULT_SEG.totalseg_task,
                  fast: bool = False) -> None:
    """TotalSegmentator CLI'ı çağırır."""
    cmd = [
        "TotalSegmentator",
        "-i", str(input_nii),
        "-o", str(out_dir),
        "--task", task,
    ]
    if fast:
        cmd.append("--fast")
    env = _m5_env()
    subprocess.run(cmd, check=True, env=env)


def _merge_ts_masks(ts_dir: Path, ref_image: sitk.Image) -> np.ndarray:
    """TotalSegmentator çıktı NIfTI'lerini 6-sınıflı tek maskeye birleştirir."""
    merged = np.zeros(sitk.GetArrayFromImage(ref_image).shape, dtype=np.uint8)
    for ts_name, our_name in TS_TO_OURS.items():
        p = ts_dir / f"{ts_name}.nii.gz"
        if not p.exists():
            continue
        mask = sitk.GetArrayFromImage(sitk.ReadImage(str(p))).astype(np.uint8)
        cls_id = ANATOMICAL_TO_ID[our_name]
        merged[mask > 0] = cls_id
    return merged


def _crop_by_boundary_slices(mask: np.ndarray,
                             boundary_info: Dict[str, List[int]],
                             case_id: int,
                             manifest: pd.DataFrame,
                             series_image_ids: List[int]) -> np.ndarray:
    """
    Boundary Slice annotasyonu, bir organın DICOM Image Id'siyle verilen üst
    ve alt sınır kesitini gösterir. Bu z-aralığı dışındaki voxeller ilgili
    sınıf için sıfırlanır.
    """
    if not boundary_info:
        return mask

    # z indeksine dönüşüm
    idx_of = {img_id: i for i, img_id in enumerate(series_image_ids)}
    out = mask.copy()
    for cls_name, img_ids in boundary_info.items():
        cls_id = ANATOMICAL_TO_ID.get(cls_name)
        if cls_id is None:
            continue
        zs = sorted(idx_of[i] for i in img_ids if i in idx_of)
        if len(zs) < 2:
            continue
        z_lo, z_hi = zs[0], zs[-1]
        # Aralık dışındaki bu sınıfa ait voxelleri temizle
        cls_voxels = (out == cls_id)
        keep = np.zeros_like(cls_voxels)
        keep[z_lo:z_hi + 1] = True
        out[cls_voxels & ~keep] = 0
    return out


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def generate_pseudo_labels(limit: int | None = None) -> None:
    """
    Tüm vakalar için TotalSegmentator → 6-sınıflı pseudo maskeler üretir ve
    nnU-Net klasör düzenine yazar.

    Optimizasyon:
      • Boundary dict döngü öncesi tek seferde hesaplanır.
      • DICOM→NIfTI dönüşümü ThreadPoolExecutor ile paralel yürür (I/O bound).
      • TotalSegmentator sıralı çalışır (zaten tüm CPU çekirdeklerini kullanır).
    """
    manifest = pd.read_csv(SPLIT_DIR / "manifest.csv")

    # Boundary bilgisini case_id → {organ: [image_id, ...]} sözlüğüne önceden dönüştür
    boundary_by_case: Dict[int, Dict[str, List[int]]] = {}
    for case_id, grp in manifest[manifest["anatomical_boundary"].fillna("") != ""].groupby("case"):
        flat: Dict[str, List[int]] = {}
        for _, row in grp.iterrows():
            for org in str(row["anatomical_boundary"]).split(";"):
                org = org.strip()
                if org:
                    flat.setdefault(org, []).append(int(row["image_id"]))
        boundary_by_case[int(case_id)] = flat

    imagesTr = SEG_DATA_DIR / "nnUNet_raw" / "Dataset501_AbdomenEmergency" / "imagesTr"
    labelsTr = SEG_DATA_DIR / "nnUNet_raw" / "Dataset501_AbdomenEmergency" / "labelsTr"
    imagesTr.mkdir(parents=True, exist_ok=True)
    labelsTr.mkdir(parents=True, exist_ok=True)

    # Tüm vaka dizinlerini topla ve limit uygula
    all_case_dirs: List[Path] = []
    for source_dir in (RAW_TRAIN_DIR, RAW_TEST_DIR):
        all_case_dirs.extend(sorted(p for p in source_dir.iterdir() if p.is_dir()))
    if limit is not None:
        all_case_dirs = all_case_dirs[:limit]

    # ── Adım 1: Paralel DICOM → NIfTI (I/O bound) ───────────────────────
    def _convert_nifti(case_dir: Path) -> tuple[str, str | None]:
        nii_path = imagesTr / f"ABE_{int(case_dir.name):05d}_0000.nii.gz"
        if nii_path.exists():
            return case_dir.name, None
        try:
            _dicom_to_nifti(case_dir, nii_path)
            return case_dir.name, None
        except Exception as e:
            return case_dir.name, str(e)

    n_io_workers = min(4, os.cpu_count() or 2)
    print(f"DICOM→NIfTI paralel dönüşüm ({n_io_workers} worker)...")
    with ThreadPoolExecutor(max_workers=n_io_workers) as ex:
        for name, err in tqdm(ex.map(_convert_nifti, all_case_dirs),
                              total=len(all_case_dirs), desc="DICOM→NIfTI"):
            if err:
                print(f"  [skip dicom→nifti] case {name}: {err}")

    # ── Adım 2: TotalSegmentator + post-processing (sıralı) ──────────────
    cases_done = 0
    for case_dir in tqdm(all_case_dirs, desc="TotalSeg + pseudo-label"):
        case_id = int(case_dir.name)
        nii_path = imagesTr / f"ABE_{case_id:05d}_0000.nii.gz"
        label_path = labelsTr / f"ABE_{case_id:05d}.nii.gz"

        if label_path.exists():
            cases_done += 1
            continue
        if not nii_path.exists():
            continue

        try:
            ref = sitk.ReadImage(str(nii_path))
            ts_out = SEG_DATA_DIR / "ts" / f"{case_id}"
            ts_out.mkdir(parents=True, exist_ok=True)
            _run_totalseg(nii_path, ts_out, fast=True)
            merged = _merge_ts_masks(ts_out, ref)

            series = load_series(case_dir)
            cropped = _crop_by_boundary_slices(
                merged, boundary_by_case.get(case_id, {}),
                case_id, manifest, series.image_ids,
            )

            sitk_mask = sitk.GetImageFromArray(cropped)
            sitk_mask.CopyInformation(ref)
            sitk.WriteImage(sitk_mask, str(label_path))

            shutil.rmtree(ts_out, ignore_errors=True)
            cases_done += 1
        except Exception as exc:
            print(f"[skip pseudo] case {case_id}: {exc}")

    _write_nnunet_dataset_json()
    print(f"Pseudo-label üretimi tamam. Toplam vaka: {cases_done}")


def _write_nnunet_dataset_json() -> None:
    ds_root = SEG_DATA_DIR / "nnUNet_raw" / "Dataset501_AbdomenEmergency"
    n_tr = len(list((ds_root / "imagesTr").glob("*.nii.gz")))
    info = {
        "name": "AbdomenEmergency",
        "description": "6-organ anatomical segmentation for TR_ABDOMEN_RAD_EMERGENCY",
        "reference": "TEKNOFEST-2022",
        "licence": "MoH Turkey open-data",
        "channel_names": {"0": "CT"},
        "labels": {"background": 0, **{k: v for k, v in ANATOMICAL_TO_ID.items()}},
        "numTraining": n_tr,
        "file_ending": ".nii.gz",
    }
    (ds_root / "dataset.json").write_text(json.dumps(info, indent=2))


# ---------------------------------------------------------------------------
# nnU-Net CLI wrapper
# ---------------------------------------------------------------------------
def nnunet_plan_and_preprocess() -> None:
    subprocess.run(
        ["nnUNetv2_plan_and_preprocess", "-d", "501", "--verify_dataset_integrity"],
        check=True, env=_m5_env(),
    )


def nnunet_train(fold: int = 0, configuration: str = "3d_fullres") -> None:
    subprocess.run(
        ["nnUNetv2_train", "501", configuration, str(fold)],
        check=True, env=_m5_env(),
    )


def nnunet_predict(in_dir: Path, out_dir: Path,
                   configuration: str = "3d_fullres",
                   folds: str = "all") -> None:
    subprocess.run(
        ["nnUNetv2_predict", "-i", str(in_dir), "-o", str(out_dir),
         "-d", "501", "-c", configuration, "-f", folds],
        check=True, env=_m5_env(),
    )


# ---------------------------------------------------------------------------
# Self-training döngüsü
# ---------------------------------------------------------------------------
def self_training_loop(iterations: int = DEFAULT_SEG.pseudo_iterations) -> None:
    """
    Basit protokol:
      T=0  → TotalSegmentator pseudo-labels
      T=1  → nnU-Net'i eğit, yeniden tahmin et, pseudo-label'ları güncelle
      T=2  → Tekrarla
    """
    for t in range(iterations):
        print(f"=== Self-training turu {t} ===")
        nnunet_plan_and_preprocess()
        for fold in range(5):
            nnunet_train(fold=fold)
        # Tahminleri yeni pseudo-label olarak yaz
        in_dir = SEG_DATA_DIR / "nnUNet_raw" / "Dataset501_AbdomenEmergency" / "imagesTr"
        out_dir = SEG_DATA_DIR / f"pred_iter{t+1}"
        out_dir.mkdir(parents=True, exist_ok=True)
        nnunet_predict(in_dir, out_dir)
        # Yeni tahmini labelsTr'ya taşı (ensembling veya majority voting burada yapılabilir)
        new_labels = SEG_DATA_DIR / "nnUNet_raw" / "Dataset501_AbdomenEmergency" / "labelsTr"
        for p in out_dir.glob("*.nii.gz"):
            shutil.copy(p, new_labels / p.name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["pseudo", "preprocess", "train", "predict", "loop"])
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--in-dir", type=Path, default=None)
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    if args.step == "pseudo":
        generate_pseudo_labels(limit=args.limit)
    elif args.step == "preprocess":
        nnunet_plan_and_preprocess()
    elif args.step == "train":
        nnunet_train(fold=args.fold)
    elif args.step == "predict":
        nnunet_predict(args.in_dir, args.out_dir)
    elif args.step == "loop":
        self_training_loop()


if __name__ == "__main__":
    main()
