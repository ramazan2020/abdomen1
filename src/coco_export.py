"""
YOLO bbox formatındaki bir fold dizinini COCO formatına çevirir.

RF-DETR ve D-FINE (ultralytics dışı dedektörler) COCO JSON annotasyonu bekler.
Bu modül DICOM'a geri dönmez — src.detection.export_yolo_dataset() tarafından
zaten üretilmiş PNG + YOLO .txt etiketlerini yeniden kullanır, sadece
annotasyon formatını dönüştürür.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List

from PIL import Image


def yolo_to_coco(images_dir: Path, labels_dir: Path,
                 class_names: List[str]) -> dict:
    """images_dir/*.png + labels_dir/*.txt (YOLO normalize bbox) → COCO dict."""
    images_dir, labels_dir = Path(images_dir), Path(labels_dir)
    coco = {
        "images": [],
        "annotations": [],
        "categories": [
            {"id": i, "name": n, "supercategory": "none"}
            for i, n in enumerate(class_names)
        ],
    }
    ann_id = 0
    img_paths = sorted(images_dir.glob("*.png"))
    for img_id, img_path in enumerate(img_paths):
        w, h = Image.open(img_path).size
        coco["images"].append({
            "id": img_id, "file_name": img_path.name, "width": w, "height": h,
        })
        lbl_path = labels_dir / (img_path.stem + ".txt")
        if not lbl_path.exists():
            continue
        text = lbl_path.read_text().strip()
        if not text:
            continue
        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            cls = int(float(parts[0]))
            cx, cy, bw, bh = (float(p) for p in parts[1:5])
            box_w, box_h = bw * w, bh * h
            x1 = cx * w - box_w / 2
            y1 = cy * h - box_h / 2
            coco["annotations"].append({
                "id": ann_id, "image_id": img_id, "category_id": cls,
                "bbox": [round(x1, 2), round(y1, 2), round(box_w, 2), round(box_h, 2)],
                "area": round(box_w * box_h, 2),
                "iscrowd": 0,
            })
            ann_id += 1
    return coco


def export_coco_split(fold_dir: Path, split: str, out_dir: Path,
                      class_names: List[str], copy_images: bool = True) -> Path:
    """
    fold_dir/images/{split}, fold_dir/labels/{split} → out_dir/{split}/ +
    out_dir/{split}/_annotations.coco.json

    Bu, RF-DETR'nin `dataset_dir` parametresinin beklediği klasör düzenidir
    (train/, valid/, test/ — her biri görüntüler + _annotations.coco.json).
    D-FINE de aynı JSON + görüntü klasörünü (farklı bir yaml config ile) okuyabilir.

    `split` ultralytics adlandırmasıyla gelir ("train"/"val"); RF-DETR "valid"
    bekler, bu yüzden çağıran taraf out_dir altında doğru klasör adını seçmelidir
    (bkz. notebook'taki SPLIT_NAME_MAP).
    """
    fold_dir, out_dir = Path(fold_dir), Path(out_dir)
    images_dir = fold_dir / "images" / split
    labels_dir = fold_dir / "labels" / split
    split_out = out_dir
    split_out.mkdir(parents=True, exist_ok=True)

    coco = yolo_to_coco(images_dir, labels_dir, class_names)
    (split_out / "_annotations.coco.json").write_text(
        json.dumps(coco, ensure_ascii=False)
    )

    if copy_images:
        for img in images_dir.glob("*.png"):
            dst = split_out / img.name
            if not dst.exists():
                shutil.copy2(img, dst)

    return split_out
