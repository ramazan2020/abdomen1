"""PyTorch Dataset'leri: multi-label sınıflandırma + detection için ortak I/O."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset

from .config import CLS_DATA_DIR, SPLIT_DIR, SUPER_CLASSES


# ---------------------------------------------------------------------------
# CLASSIFICATION DATASET
# ---------------------------------------------------------------------------
class SliceMultiLabelDataset(Dataset):
    """
    Önceden `preprocessing.export_slices` ile üretilmiş NPZ dosyalarını okur.
    Her örnek: (image [3,H,W] float32, labels [6] float32, case int, image_id int).

    Etiketler manifest.csv'den lookup ile alınır; NPZ içindeki etiket değeri
    yalnızca manifest'te kaydı olmayan negatif örnekler için kullanılır.
    """

    def __init__(
        self,
        case_ids: Sequence[int],
        data_dir: Path = CLS_DATA_DIR,
        transform=None,
        input_size: int = 384,
        manifest_csv: Path = SPLIT_DIR / "manifest.csv",
    ):
        self.data_dir = Path(data_dir)
        self.input_size = input_size
        self.transform = transform

        case_set = set(int(c) for c in case_ids)
        self.files: List[Path] = sorted(
            p for p in self.data_dir.glob("*.npz")
            if int(p.stem.split("_")[0]) in case_set
        )
        if not self.files:
            raise RuntimeError(f"{self.data_dir} altında eşleşen NPZ bulunamadı.")

        # Manifest'ten (case, image_id) → label vektörü lookup tablosu
        self._label_lookup: Dict[tuple, np.ndarray] = {}
        if Path(manifest_csv).exists():
            mdf = pd.read_csv(manifest_csv)
            mdf = mdf[mdf["case"].isin(case_set)]
            for _, row in mdf.iterrows():
                vec = np.zeros(len(SUPER_CLASSES), dtype=np.float32)
                sl = str(row.get("super_labels", ""))
                if sl and sl != "nan":
                    for s in sl.split(";"):
                        s = s.strip()
                        if s:
                            vec[int(s)] = 1.0
                self._label_lookup[(int(row["case"]), int(row["image_id"]))] = vec

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        path = self.files[idx]
        with np.load(path, allow_pickle=False) as npz:
            img = npz["image"].astype(np.float32)      # H,W,3
            labels = npz["labels"].astype(np.float32)
            case = int(npz["case"])
            image_id = int(npz["image_id"])

        # NPZ etiketi yerine manifest lookup kullan (varsa)
        key = (case, image_id)
        if key in self._label_lookup:
            labels = self._label_lookup[key]

        # HxWx3 → 3xHxW
        img_chw = np.transpose(img, (2, 0, 1))
        # Opsiyonel resize
        if img_chw.shape[-1] != self.input_size:
            img_chw = _resize_chw(img_chw, (self.input_size, self.input_size))

        tensor = torch.from_numpy(img_chw).float()
        label_t = torch.from_numpy(labels).float()

        sample = {
            "image": tensor,
            "labels": label_t,
            "case": case,
            "image_id": image_id,
            "path": str(path),
        }
        if self.transform is not None:
            sample = self.transform(sample)
        return sample


def _resize_chw(img: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
    """Basit bilinear resize — torchvision bağımlılığı gerektirmeden."""
    import cv2
    c, h, w = img.shape
    if (h, w) == size:
        return img
    out = np.zeros((c, size[0], size[1]), dtype=img.dtype)
    for i in range(c):
        out[i] = cv2.resize(img[i], (size[1], size[0]), interpolation=cv2.INTER_LINEAR)
    return out


# ---------------------------------------------------------------------------
# YARDIMCI: MANİFEST FİLTRELEME
# ---------------------------------------------------------------------------
def load_manifest(cases: Sequence[int] | None = None) -> pd.DataFrame:
    df = pd.read_csv(SPLIT_DIR / "manifest.csv")
    if cases is not None:
        df = df[df["case"].isin(cases)].reset_index(drop=True)
    return df
