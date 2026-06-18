"""
Vaka (Case Number) bazlı stratifiye edilmiş StratifiedGroupKFold + hold-out.
Aynı vakanın kesitleri ASLA birden fazla fold'a düşmez.

Negatif vakalar (manifest.csv'de var, Bilgi.xlsx'te yok) has_*=0 etiketiyle
eğitim havuzuna dahil edilir: patient-head BCE kaybı ve özgüllük ölçümü için
şarttır; saptama/bbox kaybı yalnızca annotasyonlu (pozitif) dilimlere uygulanır.

Hold-out skorlama: 5 fold modelinin ENSEMBLE AVERAGE'ı (olasılıklar ortalaması).
Her fold modeli hold-out setine uygulanır, çıktı olasılıkları ortalanır, eşik
sonradan sweep edilerek F1/AUC hesaplanır — yayın standardı.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold, train_test_split

from .config import (BILGI_XLSX, SPLIT_DIR, SUPER_CLASSES, DEFAULT_SPLIT,
                     super_id_from_raw)


# ---------------------------------------------------------------------------
# STRATUM — nadir sınıfı önceliklendiren tek etiket (StratifiedGroupKFold için)
# ---------------------------------------------------------------------------

# Sıralama: en nadir → en yüksek stratum değeri
_STRATA_PRIORITY: List[str] = [
    'acute_diverticulitis',        # ~21 vaka — en nadir
    'aortic_aneurysm_dissection',
    'acute_appendicitis',
    'acute_pancreatitis',
    'acute_cholecystitis',
    'kidney_ureter_stone',
]


def _make_strata(case_mat: pd.DataFrame) -> np.ndarray:
    """
    Her vaka için tek bir stratum etiketi üretir.
    Birden fazla patolojisi olan vakada en nadir sınıf öncelik alır.
    Negatif vakalar stratum=0.
    """
    n = len(_STRATA_PRIORITY)
    strata = []
    for _, row in case_mat.iterrows():
        s = 0
        for i, cls in enumerate(_STRATA_PRIORITY):
            if row.get(f'has_{cls}', 0) == 1:
                s = n - i   # nadir sınıf → yüksek değer
                break
        strata.append(s)
    return np.array(strata)


# ---------------------------------------------------------------------------
# NEGATİF VAKALAR
# ---------------------------------------------------------------------------

def _load_negative_cases(case_mat: pd.DataFrame,
                         manifest_dir: Path) -> pd.DataFrame:
    """
    manifest.csv'deki tüm vakalardan Bilgi.xlsx annotasyonu olmayanları
    (negatifler) has_*=0 etiketiyle döndürür.
    """
    manifest_path = manifest_dir / 'manifest.csv'
    if not manifest_path.exists():
        return pd.DataFrame()

    all_cases  = set(pd.read_csv(manifest_path)['case'].unique())
    annotated  = set(case_mat['Case Number'].unique())
    neg_cases  = sorted(all_cases - annotated)
    if not neg_cases:
        return pd.DataFrame()

    zero = {f'has_{cls}': 0 for cls in SUPER_CLASSES}
    return pd.DataFrame([{'Case Number': c, **zero} for c in neg_cases])


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
    """
    İki sayfayı birleştirir; Case Number'a kaynak öneki ekler:
      T_20001  →  Egitim (TRAININGDATA)
      C_20001  →  Yarışma (COMPETITIONDATA)
    Böylece aynı sayısal ID farklı setlerde karışmaz.
    """
    sheets = pd.read_excel(BILGI_XLSX, sheet_name=None)
    train = sheets["TRAIININGDATA"].assign(source="train")
    comp  = sheets["COMPETITIONDATA"].assign(source="comp")
    merged = pd.concat([train, comp], ignore_index=True)
    merged["Case Number"] = merged.apply(
        lambda r: f"T_{r['Case Number']}" if r["source"] == "train"
                  else f"C_{r['Case Number']}",
        axis=1,
    )
    return merged


# ---------------------------------------------------------------------------
# SPLIT
# ---------------------------------------------------------------------------

def make_splits(out_dir: Path = SPLIT_DIR,
                cfg=DEFAULT_SPLIT) -> Dict[str, Path]:
    """
    1) Annotasyonlu vakaları (T_ + C_) ve manifest.csv'deki negatif vakaları
       birleştirir.
    2) Vakaların %holdout_frac kadarını nadir sınıfa göre STRATİFİYE olarak
       hold-out'a alır.
    3) Kalan vakaları StratifiedGroupKFold(k=cfg.n_splits) ile böler;
       hem vaka sızıntısını önler hem sınıf dengesini korur.
    4) splits.csv, holdout.csv ve her fold için train/val CSV üretir.

    Hold-out skorlama: 5 fold modelinin ensemble average'ı (bkz. modül docstring).

    Returns: üretilen CSV yollarını içeren sözlük.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pozitif vakalar (Bilgi.xlsx'ten)
    all_ann  = load_merged_annotations()
    case_mat = _vaka_super_matrix(all_ann)

    # Negatif vakalar (manifest.csv'den — patient-head ve özgüllük için)
    neg_mat = _load_negative_cases(case_mat, out_dir)
    n_pos = len(case_mat)
    if not neg_mat.empty:
        case_mat = pd.concat([case_mat, neg_mat], ignore_index=True)
    n_neg = len(case_mat) - n_pos
    print(f"Splits: {n_pos} pozitif + {n_neg} negatif = {len(case_mat)} toplam vaka")

    cases  = case_mat["Case Number"].values
    strata = _make_strata(case_mat)

    # Hold-out: stratifiye (nadir sınıf her zaman temsil edilir)
    train_cases, holdout_cases = train_test_split(
        cases,
        test_size=cfg.holdout_frac,
        random_state=cfg.seed,
        shuffle=True,
        stratify=strata,
    )

    pd.DataFrame({"Case Number": holdout_cases}).to_csv(
        out_dir / "holdout.csv", index=False)

    # Train stratum: case → stratum eşlemesi üzerinden güvenli hizalama
    case_strata_map = dict(zip(cases, strata))
    train_strata    = np.array([case_strata_map[c] for c in train_cases])

    # StratifiedGroupKFold: sızıntısız + dengeli
    sgkf = StratifiedGroupKFold(n_splits=cfg.n_splits)
    fold_assignments = np.full(len(train_cases), -1, dtype=np.int8)
    for fold_idx, (_, val_idx) in enumerate(
        sgkf.split(X=train_cases, y=train_strata, groups=train_cases)
    ):
        fold_assignments[val_idx] = fold_idx

    splits = pd.DataFrame({
        "Case Number": train_cases,
        "fold": fold_assignments,
    })
    splits.to_csv(out_dir / "splits.csv", index=False)

    # Fold bazlı CSV'ler
    paths = {"holdout": out_dir / "holdout.csv", "splits": out_dir / "splits.csv"}
    for fold in range(cfg.n_splits):
        val_cases        = splits.loc[splits.fold == fold,  "Case Number"].values
        train_fold_cases = splits.loc[splits.fold != fold, "Case Number"].values
        for name, cs in [("train", train_fold_cases), ("val", val_cases)]:
            p = out_dir / f"fold{fold}_{name}.csv"
            pd.DataFrame({"Case Number": cs}).to_csv(p, index=False)
            paths[f"fold{fold}_{name}"] = p
    return paths


def load_fold(fold: int, split: str) -> List[str]:
    """fold ∈ [0, n_splits), split ∈ {'train','val'}. "T_20001" formatında döner."""
    p = SPLIT_DIR / f"fold{fold}_{split}.csv"
    return pd.read_csv(p)["Case Number"].astype(str).tolist()


def load_holdout() -> List[str]:
    return pd.read_csv(SPLIT_DIR / "holdout.csv")["Case Number"].astype(str).tolist()


def raw_case_id(case: str) -> int:
    """'T_20001' → 20001  |  'C_20001' → 20001"""
    return int(case.split("_", 1)[1])


if __name__ == "__main__":
    paths = make_splits()
    print("Oluşturulan split dosyaları:")
    for k, v in paths.items():
        print(f"  {k}: {v}")
