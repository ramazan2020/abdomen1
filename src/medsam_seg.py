"""
MedSAM (box-prompted) 2D dilim segmentasyonu.

`weak_seg.py`'deki organ-maskesi ∩ BB yaklaşımı yalnızca organın tamamını
(BB ile kırpılmış hâliyle) etiketliyor; lezyonun kendi sınırını bilmiyor.
Bu modül, BB annotasyonlu her kesitte MedSAM'e kutuyu prompt olarak verip
piksel-hassas bir lezyon maskesi üretir. `weak_seg._make_disease_mask` bu
maskeyi organ maskesiyle kesiştirerek nihai etiketi oluşturur.

Model: wanglab/medsam-vit-base (HuggingFace transformers SamModel/SamProcessor
üzerinden) — SAM mimarisi, medikal görüntülerle (BT dahil) box-prompt
segmentasyonu için fine-tune edilmiş.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Tuple

import numpy as np

from .config import DEFAULT_WINDOWS, Window
from .dicom_utils import window_hu

MODEL_ID = "wanglab/medsam-vit-base"


@lru_cache(maxsize=1)
def _load_medsam(device: str):
    from transformers import SamModel, SamProcessor
    model = SamModel.from_pretrained(MODEL_ID).to(device).eval()
    processor = SamProcessor.from_pretrained(MODEL_ID)
    return model, processor


def hu_slice_to_rgb(hu: np.ndarray, window: Window = DEFAULT_WINDOWS[0]) -> np.ndarray:
    """HU dilimini tek pencere ile [0,255] gri-RGB'ye çevirir (MedSAM girişi)."""
    gray = (window_hu(hu, window) * 255.0).astype(np.uint8)
    return np.stack([gray, gray, gray], axis=-1)


def medsam_box_to_mask(hu_slice: np.ndarray,
                       box_xyxy: Tuple[int, int, int, int],
                       device: str = "cpu") -> np.ndarray:
    """
    Tek bir BT kesiti + BB (x1,y1,x2,y2) → MedSAM ile ikili lezyon maskesi.

    Kutu dışına taşan/ters koordinatlar kliplenir. Kutu alanı 0 ise
    (annotasyon hatası) boş maske döner.
    """
    import torch

    h, w = hu_slice.shape
    x1, y1, x2, y2 = box_xyxy
    x1, x2 = sorted((max(0, min(x1, w - 1)), max(0, min(x2, w))))
    y1, y2 = sorted((max(0, min(y1, h - 1)), max(0, min(y2, h))))
    if x2 <= x1 or y2 <= y1:
        return np.zeros((h, w), dtype=np.uint8)

    model, processor = _load_medsam(device)
    rgb = hu_slice_to_rgb(hu_slice)

    inputs = processor(rgb, input_boxes=[[[x1, y1, x2, y2]]],
                       return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs, multimask_output=False)

    masks = processor.image_processor.post_process_masks(
        outputs.pred_masks.cpu(),
        inputs["original_sizes"].cpu(),
        inputs["reshaped_input_sizes"].cpu(),
    )
    return masks[0][0, 0].numpy().astype(np.uint8)
