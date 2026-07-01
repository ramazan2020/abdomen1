"""
YOLO segmentasyon (poligon) veri hazırlığı ve eğitim sarmalayıcısı.

Ground truth poligon kaynağı: bounding box köşeleri.
Bilgi.xlsx içinde piksel-seviyeli organ/lezyon konturu yoktur; mevcut bbox
annotasyonu zaten hastalığın 2D sınırını verdiği için, segmentasyon poligonu
doğrudan bbox'un 4 köşesinden (dikdörtgen) üretilir. YOLO-seg formatı herhangi
bir kapalı poligonu kabul ettiğinden bu, ultralytics segment trainer'ı ile
birebir uyumludur — ek bağımlılık (TotalSegmentator vb.) gerekmez.

Görüntüler `export_yolo_dataset()` (src.detection) ile birebir aynı pencereleme
ve PNG üretimini kullanır; yalnızca etiket formatı bbox→poligona çevrilir.
"""
from __future__ import annotations

import argparse
import multiprocessing
import platform
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

import pandas as pd
from tqdm import tqdm

from .config import SEG_DATA_DIR, SPLIT_DIR, SUPER_CLASSES
from .detection import _safe_bboxes, _write_slice_png

SEG_YOLO_DATA_DIR = SEG_DATA_DIR / "yolo_seg"


# ---------------------------------------------------------------------------
# VERİ HAZIRLIĞI
# ---------------------------------------------------------------------------
def _process_manifest_row(args: tuple):
    """ProcessPoolExecutor worker'ı: tek manifest satırını PNG + poligon label'a dönüştürür."""
    row_dict, split, fold_dir_str, include_val_negatives = args
    fold_dir = Path(fold_dir_str)
    row = pd.Series(row_dict)

    bboxes_raw = _safe_bboxes(row.get("bboxes"))
    has_bbox = bool(bboxes_raw)
    if not include_val_negatives and split == "val" and not has_bbox:
        return None

    try:
        img_path, h, w = _write_slice_png(row, fold_dir / "images" / split)
        label_path = fold_dir / "labels" / split / (img_path.stem + ".txt")
        _write_yolo_seg_label(bboxes_raw, h, w, label_path)
        return str(img_path)
    except Exception as exc:
        return f"ERR:{row['dicom_path']}:{exc}"


def export_yolo_seg_dataset(fold: int,
                            out_root: Path = SEG_YOLO_DATA_DIR,
                            include_val_negatives: bool = True,
                            bbox_only: bool = True,
                            include_train_negatives: bool = False) -> Path:
    """
    Ultralytics YOLO-seg'in beklediği yapıyı kurar:
        out_root/foldN/
            images/train/*.png
            images/val/*.png
            labels/train/*.txt   ← "cls x1 y1 x2 y2 x3 y3 x4 y4" (normalize poligon)
            labels/val/*.txt
            dataset.yaml

    bbox_only=True (varsayılan): yalnızca Type == "Bounding Box" annotasyonu
    olan kesitler işlenir (src.detection.export_yolo_dataset ile aynı filtre).

    include_train_negatives=True: bbox annotasyonu olmayan vakaların tüm
    dilimleri boş label dosyasıyla train setine eklenir (false positive bastırma).
    """
    out_root = Path(out_root)
    fold_dir = out_root / f"fold{fold}"
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        p = fold_dir / sub
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    for cache in (fold_dir / "labels").glob("*.cache"):
        cache.unlink(missing_ok=True)

    manifest_full = pd.read_csv(SPLIT_DIR / "manifest.csv")

    if bbox_only:
        n_before = len(manifest_full)
        manifest = manifest_full[manifest_full["bboxes"].fillna("").str.strip() != ""].copy()
        n_skipped = n_before - len(manifest)
        if n_skipped:
            print(f"BBox filtresi: {n_skipped:,} bbox'sız satır dışlandı "
                  f"→ {len(manifest):,} kesit işlenecek")
    else:
        manifest = manifest_full

    train_cases = set(pd.read_csv(SPLIT_DIR / f"fold{fold}_train.csv")["Case Number"])
    val_cases   = set(pd.read_csv(SPLIT_DIR / f"fold{fold}_val.csv")["Case Number"])

    tasks: List[tuple] = []
    for _, row in manifest.iterrows():
        case = str(row["case"])
        if case in train_cases:
            split = "train"
        elif case in val_cases:
            split = "val"
        else:
            continue
        tasks.append((row.to_dict(), split, str(fold_dir), include_val_negatives))

    if include_train_negatives and bbox_only:
        _cases_with_bbox = set(manifest["case"].astype(str))
        _neg_train = {c for c in train_cases if c not in _cases_with_bbox}
        if _neg_train:
            neg_rows = manifest_full[manifest_full["case"].astype(str).isin(_neg_train)]
            print(f"Negatif vakalar: {len(_neg_train)} vaka, "
                  f"{len(neg_rows):,} dilim → train (boş label)")
            for _, row in neg_rows.iterrows():
                tasks.append((row.to_dict(), "train", str(fold_dir), True))

    cpu_count = multiprocessing.cpu_count() or 2
    if platform.system() == "Darwin":
        n_workers = min(6, cpu_count)
        ctx = multiprocessing.get_context("spawn")
        Executor = ProcessPoolExecutor
        executor_kwargs: dict = {"max_workers": n_workers, "mp_context": ctx}
    else:
        n_workers = min(16, cpu_count * 4)
        Executor = ThreadPoolExecutor
        executor_kwargs = {"max_workers": n_workers}

    with Executor(**executor_kwargs) as executor:
        futures = {executor.submit(_process_manifest_row, t): t for t in tasks}
        for fut in tqdm(as_completed(futures), total=len(tasks), desc=f"YOLO-seg fold{fold}"):
            result = fut.result()
            if result and result.startswith("ERR:"):
                print(f"[skip] {result[4:]}")

    _write_dataset_yaml(fold_dir)
    return fold_dir


def _write_yolo_seg_label(bboxes_raw: str, h: int, w: int, out: Path) -> None:
    """
    Manifest'in `bboxes` sütununu YOLO-seg poligon formatına çevirir.

    Her kutu (x1,y1,x2,y2) saat yönünde 4 köşeli normalize poligona dönüşür:
        (x1,y1) → (x2,y1) → (x2,y2) → (x1,y2)

    Aynı güvenlik garantisi src.detection._write_yolo_label ile özdeştir:
    bboxes sütunu sadece Type == "Bounding Box" satırlarından dolduğu için
    Boundary Slice kaynaklı koordinat asla buraya girmez.
    """
    seen: set = set()
    lines: List[str] = []
    if bboxes_raw:
        for token in bboxes_raw.split("|"):
            token = token.strip()
            if not token or token.lower() == "nan":
                continue
            parts = token.split(",")
            if len(parts) != 5:
                continue
            if any(v.strip().lower() in ("nan", "", "none") for v in parts):
                continue
            try:
                sid, x1, y1, x2, y2 = (int(float(v)) for v in parts)
            except (ValueError, TypeError):
                continue
            if not (0 <= sid <= 5):
                continue
            if x2 <= x1 or y2 <= y1:
                continue
            key = (sid, x1, y1, x2, y2)
            if key in seen:
                continue
            seen.add(key)

            corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            norm = " ".join(f"{cx / w:.6f} {cy / h:.6f}" for cx, cy in corners)
            lines.append(f"{sid} {norm}")
    out.write_text("\n".join(lines))


def _write_dataset_yaml(fold_dir: Path) -> None:
    yaml = [
        f"path: {fold_dir.resolve()}",
        "train: images/train",
        "val: images/val",
        "names:",
    ]
    for i, c in enumerate(SUPER_CLASSES):
        yaml.append(f"  {i}: {c}")
    (fold_dir / "dataset.yaml").write_text("\n".join(yaml) + "\n")


# ---------------------------------------------------------------------------
# EĞİTİM
# ---------------------------------------------------------------------------
def train_yolo_seg(fold: int, model: str = "yolo11m-seg.pt",
                   img_size: int = 512, epochs: int = 100,
                   batch_size: int = 16, project: str = "runs/seg",
                   data_dir: Path = SEG_YOLO_DATA_DIR, **train_kwargs) -> Path:
    """Ultralytics YOLO-seg eğitimi. `model` adı `-seg` ekiyle bitmelidir."""
    import torch
    from ultralytics import YOLO

    fold_dir = Path(data_dir) / f"fold{fold}"
    if not (fold_dir / "dataset.yaml").exists():
        export_yolo_seg_dataset(fold, out_root=Path(data_dir))

    if torch.backends.mps.is_available():
        device = "mps"
    elif torch.cuda.is_available():
        device = "0"
    else:
        device = "cpu"

    yolo_model = YOLO(model)
    run_name = f"fold{fold}_{Path(model).stem}"
    yolo_model.train(
        data=str(fold_dir / "dataset.yaml"),
        imgsz=img_size,
        epochs=epochs,
        batch=batch_size,
        mosaic=0.0, mixup=0.0, fliplr=0.0, flipud=0.0,
        hsv_h=0.0, hsv_s=0.0, hsv_v=0.4, degrees=10.0,
        project=project,
        name=run_name,
        seed=42,
        deterministic=False,
        device=device,
        amp=True,
        **train_kwargs,
    )
    return Path(yolo_model.trainer.save_dir) / "weights" / "best.pt"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["export", "train"])
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--model", type=str, default="yolo11m-seg.pt")
    args = ap.parse_args()

    if args.step == "export":
        d = export_yolo_seg_dataset(args.fold)
        print("YOLO-seg dataset hazır:", d)
    elif args.step == "train":
        w = train_yolo_seg(args.fold, model=args.model)
        print("YOLO-seg best weights:", w)


if __name__ == "__main__":
    main()
