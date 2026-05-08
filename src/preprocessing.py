"""
Aşama 1: Bilgi.xlsx'teki ham annotasyonları birleştirip her kesiti
multi-label + bbox etiketi ile bir manifest'e yazar.

Aşama 2: İlgili kesitleri (annotasyonu olan kesitler + negatif örnekleme)
3 kanallı NPZ olarak kaydeder.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import (ANATOMICAL_TO_ID, CLS_DATA_DIR, DEFAULT_WINDOWS,
                     RAW_PATHOLOGY_TO_SUPER, RAW_TEST_DIR, RAW_TRAIN_DIR,
                     SPLIT_DIR, SUPER_CLASSES)
from .dicom_utils import (dicom_to_hu, hu_to_three_channel, parse_bbox,
                          read_dicom)
from .splits import load_merged_annotations


# ---------------------------------------------------------------------------
# MANİFEST
# ---------------------------------------------------------------------------
def build_manifest(out_path: Path = SPLIT_DIR / "manifest.csv") -> Path:
    """
    Her (Case Number, Image Id) satırı için:
        - source: train / comp
        - dicom_path: diske göre tam yol
        - super_labels: "0;2" gibi semicolon ayrık üst sınıf ID'leri
        - bboxes: "0,10,20,30,40|2,100,120,130,140" (super_id,x1,y1,x2,y2)
        - anatomical_boundary: "Abdominal Aorta;Colon"
    şeklinde derlenmiş bir CSV üretir. Bu dosya tüm alt işlemlerin girdisidir.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ann = load_merged_annotations()

    # DICOM yolu çözümle
    def _dicom_path(row):
        base = RAW_TRAIN_DIR if row["source"] == "train" else RAW_TEST_DIR
        return str(base / str(row["Case Number"]) / f"{row['Image Id']}.dcm")

    ann["dicom_path"] = ann.apply(_dicom_path, axis=1)

    records: List[dict] = []
    group = ann.groupby(["Case Number", "Image Id", "source", "dicom_path"])
    for (case, img, source, dpath), grp in group:
        super_ids = set()
        bbox_strs: List[str] = []
        anat_boundaries: List[str] = []

        for _, row in grp.iterrows():
            cls = row["Class"]
            if row["Type"] == "Bounding Box":
                sid = RAW_PATHOLOGY_TO_SUPER.get(cls)
                if sid is None:
                    continue
                bb = parse_bbox(str(row["Data"]))
                if bb is None:
                    continue
                super_ids.add(sid)
                bbox_strs.append(f"{sid},{bb[0]},{bb[1]},{bb[2]},{bb[3]}")
            elif row["Type"] == "Boundary Slice":
                if cls in ANATOMICAL_TO_ID:
                    anat_boundaries.append(cls)

        records.append({
            "case": int(case),
            "image_id": int(img),
            "source": source,
            "dicom_path": dpath,
            "super_labels": ";".join(str(s) for s in sorted(super_ids)),
            "bboxes": "|".join(bbox_strs),
            "anatomical_boundary": ";".join(anat_boundaries),
        })

    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)
    print(f"Manifest yazıldı: {out_path}  (satır: {len(df)})")
    return out_path


# ---------------------------------------------------------------------------
# SLICE → NPZ
# ---------------------------------------------------------------------------
def _encode_multilabel(super_labels_str: str) -> np.ndarray:
    vec = np.zeros(len(SUPER_CLASSES), dtype=np.uint8)
    if not super_labels_str or pd.isna(super_labels_str):
        return vec
    for s in str(super_labels_str).split(";"):
        if s != "":
            vec[int(s)] = 1
    return vec


def export_slices(manifest_csv: Path = SPLIT_DIR / "manifest.csv",
                  out_dir: Path = CLS_DATA_DIR,
                  include_negative_sampling: int = 0) -> None:
    """
    Manifest'teki her satır için DICOM'u okuyup 3-kanallı float16 NPZ yazar.
    include_negative_sampling > 0 ise, her vaka için annotasyonsuz kesitlerden
    `n` adet rastgele örnek ekler (hard-negative mining için faydalı).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(manifest_csv)
    for _, row in tqdm(df.iterrows(), total=len(df), desc="exporting slices"):
        dpath = Path(row["dicom_path"])
        if not dpath.exists():
            continue
        try:
            ds = read_dicom(dpath)
            hu = dicom_to_hu(ds)
            img = hu_to_three_channel(hu, DEFAULT_WINDOWS)  # HxWx3, float32
        except Exception as exc:
            print(f"[skip] {dpath}: {exc}")
            continue

        labels = _encode_multilabel(row["super_labels"])
        out_path = out_dir / f"{row['case']}_{row['image_id']}.npz"
        np.savez_compressed(
            out_path,
            image=img.astype(np.float16),
            labels=labels,
            case=int(row["case"]),
            image_id=int(row["image_id"]),
            source=row["source"],
        )

    if include_negative_sampling > 0:
        # Annotasyonsuz kesitlerden örnekleme
        _append_random_negatives(df, out_dir, n_per_case=include_negative_sampling)


def _append_random_negatives(manifest_df: pd.DataFrame,
                             out_dir: Path,
                             n_per_case: int) -> None:
    """Her vaka için ek olarak annotasyonsuz kesitler çeker."""
    import random
    rng = random.Random(0)
    ann_keys = set(
        (int(r["case"]), int(r["image_id"])) for _, r in manifest_df.iterrows()
    )

    from .config import RAW_TRAIN_DIR, RAW_TEST_DIR
    for base, source in [(RAW_TRAIN_DIR, "train"), (RAW_TEST_DIR, "comp")]:
        for case_dir in tqdm(sorted(p for p in base.iterdir() if p.is_dir()),
                             desc=f"neg {source}"):
            case = int(case_dir.name)
            dcms = [p for p in case_dir.iterdir() if p.suffix.lower() == ".dcm"]
            neg = [p for p in dcms if (case, int(p.stem)) not in ann_keys]
            rng.shuffle(neg)
            for p in neg[:n_per_case]:
                try:
                    ds = read_dicom(p)
                    hu = dicom_to_hu(ds)
                    img = hu_to_three_channel(hu, DEFAULT_WINDOWS)
                except Exception:
                    continue
                out = out_dir / f"{case}_{p.stem}.npz"
                np.savez_compressed(
                    out,
                    image=img.astype(np.float16),
                    labels=np.zeros(len(SUPER_CLASSES), dtype=np.uint8),
                    case=case,
                    image_id=int(p.stem),
                    source=source,
                )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["manifest", "export", "all"])
    ap.add_argument("--negatives", type=int, default=0,
                    help="her vaka için eklenecek rastgele negatif kesit sayısı")
    args = ap.parse_args()

    if args.step in ("manifest", "all"):
        build_manifest()
    if args.step in ("export", "all"):
        export_slices(include_negative_sampling=args.negatives)


if __name__ == "__main__":
    main()
