"""
2D bounding box annotasyonlarını z-ekseni boyunca 3D'ye yükseltme.

Ana sınıf: BboxLifter

Algoritma:
  Aynı vaka + aynı sınıfa ait 2D bbox'lar z-pozisyonuna göre sıralanır.
  Ardışık (|Δz| ≤ delta_z) ve üst üste binen (2D IoU ≥ iou_th) bbox'lar
  aynı lezyona ait kabul edilir.
  Her grup için (x1,y1,z1) → (x2,y2,z2) 3D bbox üretilir.

Bu modül; notebook'lardaki lift_2d_to_3d() fonksiyonunun tek yetkili kaynağıdır.
BboxLifter ayrıca nnU-Net için semantic segmentasyon maskesi de üretir.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .config import YARISMA_DIR, EGITIM_DIR
from .dicom_utils import DicomVolume


def _2d_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = (ax2 - ax1) * (ay2 - ay1)
    ub = (bx2 - bx1) * (by2 - by1)
    return inter / max(ua + ub - inter, 1e-6)


class BboxLifter:
    """
    Manifest'teki 2D bounding box annotasyonlarını 3D'ye yükseltir.

    T_ (eğitim) ve C_ (yarışma) vakalarını destekler; DICOM klasörünü
    öneke göre otomatik seçer (egitim_dir / yarisma_dir).

    Kullanım:
        lifter = BboxLifter(manifest)                    # varsayılan config yolları
        boxes  = lifter.lift("T_20001")                  # List[Dict]
        boxes  = lifter.lift("C_20001")                  # yarışma vakası
        mask   = lifter.build_semantic_mask("T_20001", shape=(300, 512, 512))

    Her kutu sözlüğü şu anahtarları içerir:
        class, x1, y1, z1, x2, y2, z2, n_slices
    """

    def __init__(
        self,
        manifest: pd.DataFrame,
        egitim_dir: Path | None = None,
        yarisma_dir: Path | None = None,
        delta_z: int = 2,
        iou_th: float = 0.3,
    ) -> None:
        self.manifest = manifest
        self.egitim_dir = Path(egitim_dir) if egitim_dir else EGITIM_DIR
        self.yarisma_dir = Path(yarisma_dir) if yarisma_dir else YARISMA_DIR
        self.delta_z = delta_z
        self.iou_th = iou_th
        self._z_cache: Dict[str, Dict[int, int]] = {}

    # ------------------------------------------------------------------
    # Dahili: z-haritası (önbellekli)
    # ------------------------------------------------------------------
    def _get_z_map(self, case: str) -> Dict[int, int]:
        if case not in self._z_cache:
            raw = str(case).split("_", 1)[-1]       # "T_20001" → "20001"
            base = self.yarisma_dir if case.startswith("C_") else self.egitim_dir
            vol = DicomVolume(base / raw)
            self._z_cache[case] = vol.z_map
        return self._z_cache[case]

    # ------------------------------------------------------------------
    # Genel API
    # ------------------------------------------------------------------
    def lift(self, case: str) -> List[Dict]:
        """
        Belirtilen vaka için 3D bounding box listesi döner.

        T_ (eğitim) ve C_ (yarışma) vakalarını destekler;
        boş olmayan bboxes satırları kullanılır.
        """
        z_map = self._get_z_map(case)
        sub = self.manifest[
            (self.manifest["case"] == case)
            & (self.manifest["bboxes"].fillna("").astype(str) != "")
        ]

        # (sınıf, x1, y1, x2, y2, z-index) demetleri
        items: List[Tuple[int, int, int, int, int, int]] = []
        for _, row in sub.iterrows():
            z = z_map.get(int(row["image_id"]))
            if z is None:
                continue
            for bb_str in str(row["bboxes"]).split("|"):
                parts = bb_str.strip().split(",")
                if len(parts) < 5:
                    continue
                try:
                    sid, x1, y1, x2, y2 = (int(float(v)) for v in parts[:5])
                except (ValueError, TypeError):
                    continue
                if x2 > x1 and y2 > y1:
                    items.append((sid, x1, y1, x2, y2, z))

        return self._group_to_3d(items)

    def build_semantic_mask(
        self, case: str, volume_shape: Tuple[int, int, int]
    ) -> np.ndarray:
        """
        Vaka için (Z, Y, X) boyutlu uint8 semantic segmentasyon maskesi üretir.

        Etiket kuralı: class indeksi 0-indexed → maske değeri 1-indexed (nnU-Net).
        Birden fazla sınıf çakışırsa son yazılan sınıf geçerlidir (nadir durum).
        """
        mask = np.zeros(volume_shape, dtype=np.uint8)
        for b in self.lift(case):
            label = int(b["class"]) + 1
            z1 = int(b["z1"]); z2 = min(int(b["z2"]) + 1, volume_shape[0])
            y1 = int(b["y1"]); y2 = min(int(b["y2"]) + 1, volume_shape[1])
            x1 = int(b["x1"]); x2 = min(int(b["x2"]) + 1, volume_shape[2])
            mask[z1:z2, y1:y2, x1:x2] = label
        return mask

    # ------------------------------------------------------------------
    # Dahili: gruplama algoritması
    # ------------------------------------------------------------------
    def _group_to_3d(
        self, items: List[Tuple[int, int, int, int, int, int]]
    ) -> List[Dict]:
        boxes_3d: List[Dict] = []
        for sid in set(it[0] for it in items):
            cls_items = sorted(
                [it for it in items if it[0] == sid], key=lambda x: x[5]
            )
            used: set = set()
            for i, it in enumerate(cls_items):
                if i in used:
                    continue
                grp = [it]
                used.add(i)
                for j in range(i + 1, len(cls_items)):
                    if j in used:
                        continue
                    last = grp[-1]
                    if cls_items[j][5] - last[5] <= self.delta_z:
                        if _2d_iou(last[1:5], cls_items[j][1:5]) >= self.iou_th:
                            grp.append(cls_items[j])
                            used.add(j)
                    else:
                        break
                boxes_3d.append({
                    "class":    sid,
                    "x1": min(g[1] for g in grp),
                    "y1": min(g[2] for g in grp),
                    "z1": min(g[5] for g in grp),
                    "x2": max(g[3] for g in grp),
                    "y2": max(g[4] for g in grp),
                    "z2": max(g[5] for g in grp),
                    "n_slices": len(grp),
                })
        return boxes_3d
