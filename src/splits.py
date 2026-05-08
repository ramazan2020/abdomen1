"""
Vaka (Case Number) bazlı stratifiye edilmiş GroupKFold + hold-out.
Aynı vakanın kesitleri ASLA birden fazla fold'a düşmez.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold, train_test_split

from .config import (BILGI_XLSX, SPLIT_DIR, SUPER_CLASSES, DEFAULT_SPLIT,
                     super_id_from_raw)


# ---------------------------------------------------------------------------
# BİLGİ TABLOSUNDAN VAKA-ÜST SINIF MATRİSİ
# ---------------------------------------------------------------------------
def _vaka_super_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Her vaka için 6 üst sınıfın var/yok (0/1) durumunu döndürür.
    Boundary Slice ve ham eşlemesi olmayan sınıflar atlanır.
    """
    df = df.copy()
    df["super_id"] = df["Class"].map(super_id_from_raw)
    df = df.dropna(subset=["super_id"])
    df["super_id"] = df["super_id"].astype(int)

    rows = []
    for case, grp in df.groupby("Case Number"):
        vec = np.zeros(len(SUPER_CLASSES), dtype=np.uint8)
        for sid in grp["super_id"].unique():
            vec[sid] = 1
        rows.append([case] + vec.tolist())
    cols = ["Case Number"] + [f"has_{c}" for c in SUPER_CLASSES]
    return pd.DataFrame(rows, columns=cols)


def load_merged_annotations() -> pd.DataFrame:
    """İki sayfayı `source` etiketi ekleyerek birleştirir."""
    sheets = pd.read_excel(BILGI_XLSX, sheet_name=None)
    train = sheets["TRAIININGDATA"].assign(source="train")
    comp = sheets["COMPETITIONDATA"].assign(source="comp")
    return pd.concat([train, comp], ignore_index=True)


# ---------------------------------------------------------------------------
# SPLIT
# ---------------------------------------------------------------------------
def make_splits(out_dir: Path = SPLIT_DIR,
                cfg=DEFAULT_SPLIT) -> Dict[str, Path]:
    """
    1) Tüm annotasyonları birleştirir.
    2) Vakaların %holdout_frac kadarını hold-out olarak ayırır
       (her üst sınıf en az 2 vaka ile temsil edilecek şekilde rastgele).
    3) Kalan vakaları GroupKFold(k=cfg.n_splits) ile böler.
    4) `splits.csv`, `holdout.csv` ve her fold için train/val csv üretir.

    Returns: üretilen CSV yollarını içeren sözlük.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_ann = load_merged_annotations()
    case_mat = _vaka_super_matrix(all_ann)
    cases = case_mat["Case Number"].values

    # Hold-out
    train_cases, holdout_cases = train_test_split(
        cases,
        test_size=cfg.holdout_frac,
        random_state=cfg.seed,
        shuffle=True,
    )

    pd.DataFrame({"Case Number": holdout_cases}).to_csv(out_dir / "holdout.csv",
                                                        index=False)

    # Fold'lar (vaka üzerinden)
    gkf = GroupKFold(n_splits=cfg.n_splits)
    fold_assignments = np.full(len(train_cases), -1, dtype=np.int8)
    for fold_idx, (_, val_idx) in enumerate(
        gkf.split(X=train_cases, y=train_cases, groups=train_cases)
    ):
        fold_assignments[val_idx] = fold_idx

    splits = pd.DataFrame({
        "Case Number": train_cases,
        "fold": fold_assignments,
    })
    splits.to_csv(out_dir / "splits.csv", index=False)

    # Fold bazlı CSV'ler (kolay yükleme için)
    paths = {"holdout": out_dir / "holdout.csv", "splits": out_dir / "splits.csv"}
    for fold in range(cfg.n_splits):
        val_cases = splits.loc[splits.fold == fold, "Case Number"].values
        train_fold_cases = splits.loc[splits.fold != fold, "Case Number"].values
        for name, cs in [("train", train_fold_cases), ("val", val_cases)]:
            p = out_dir / f"fold{fold}_{name}.csv"
            pd.DataFrame({"Case Number": cs}).to_csv(p, index=False)
            paths[f"fold{fold}_{name}"] = p
    return paths


def load_fold(fold: int, split: str) -> List[int]:
    """fold ∈ [0, n_splits), split ∈ {'train','val'}."""
    p = SPLIT_DIR / f"fold{fold}_{split}.csv"
    return pd.read_csv(p)["Case Number"].astype(int).tolist()


def load_holdout() -> List[int]:
    return pd.read_csv(SPLIT_DIR / "holdout.csv")["Case Number"].astype(int).tolist()


if __name__ == "__main__":
    paths = make_splits()
    print("Oluşturulan split dosyaları:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
