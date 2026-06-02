"""
YOLOv8 için veri hazırlığı ve eğitim sarmalayıcısı.

Özetle:
1. `export_yolo_dataset(fold)` — Bilgi.xlsx'tan manifest'i okur, her annotasyonlu
   kesiti PNG olarak yazar ve her kesit için YOLO txt etiketi üretir (6 üst sınıf).
2. `train_yolo(fold)` — Ultralytics YOLO'yu çağırır.
3. `predict_volume(case_id)` — Bir vakanın tüm kesitlerinde inference yapar;
   3B post-processing ile ardışık kesit süreklilik kuralı uygular.
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import platform
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from .config import (DEFAULT_DET, DEFAULT_WINDOWS, DET_DATA_DIR,
                     RAW_PATHOLOGY_TO_SUPER, RAW_TEST_DIR, RAW_TRAIN_DIR,
                     SPLIT_DIR, SUPER_CLASSES)
from .dicom_utils import (bbox_xyxy_to_yolo, dicom_to_hu, hu_to_three_channel,
                          parse_bbox, read_dicom)


# ---------------------------------------------------------------------------
# VERİ HAZIRLIĞI
# ---------------------------------------------------------------------------
def _safe_bboxes(raw) -> str:
    """NaN / None / 'nan' string → boş string; geçerli değeri string olarak döner."""
    if raw is None:
        return ""
    # float NaN kontrolü (pandas CSV okuyunca gelir)
    try:
        import math
        if isinstance(raw, float) and math.isnan(raw):
            return ""
    except Exception:
        pass
    s = str(raw).strip()
    return "" if s.lower() == "nan" else s


def _process_manifest_row(args: tuple):
    """ProcessPoolExecutor worker'ı: tek manifest satırını PNG + label'a dönüştürür."""
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
        _write_yolo_label(bboxes_raw, h, w, label_path)
        return str(img_path)
    except Exception as exc:
        return f"ERR:{row['dicom_path']}:{exc}"


def export_yolo_dataset(fold: int,
                        out_root: Path = DET_DATA_DIR,
                        include_val_negatives: bool = True,
                        bbox_only: bool = True) -> Path:
    """
    Ultralytics YOLOv8'in beklediği yapıyı kurar:
        out_root/foldN/
            images/train/*.png
            images/val/*.png
            labels/train/*.txt
            labels/val/*.txt
            dataset.yaml

    DICOM→PNG dönüşümü ProcessPoolExecutor ile paralel işlenir.

    bbox_only=True (varsayılan): yalnızca Type == "Bounding Box" annotasyonu
    olan kesitler işlenir; Boundary Slice'a ait kesitler YOLO'ya girmez.
    """
    out_root = Path(out_root)
    fold_dir = out_root / f"fold{fold}"
    for sub in ("images/train", "images/val", "labels/train", "labels/val"):
        p = fold_dir / sub
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)
    # YOLO stale cache dosyalarını temizle (labels/ altında kalır, shutil.rmtree etkilemez)
    for cache in (fold_dir / "labels").glob("*.cache"):
        cache.unlink(missing_ok=True)

    manifest = pd.read_csv(SPLIT_DIR / "manifest.csv")

    # Aynı case+image_id farklı setlerde (train/comp) farklı resimler olabilir;
    # fold split'leri sadece eğitim setini kapsadığından comp satırları dışlanır.
    manifest = manifest[manifest["source"] == "train"].copy()

    # ── Bounding Box filtresi ─────────────────────────────────────────────
    # YOLO'ya yalnızca Type == "Bounding Box" annotasyonu olan kesitler girer.
    # preprocessing.build_manifest() zaten bu garantiyi sağlar; buradaki filtre
    # ek savunma katmanıdır (Boundary Slice satırları bboxes sütununu boş bırakır).
    if bbox_only:
        n_before = len(manifest)
        manifest = manifest[manifest["bboxes"].fillna("").str.strip() != ""].copy()
        n_skipped = n_before - len(manifest)
        if n_skipped:
            print(f"BBox filtresi: {n_skipped:,} bbox'sız satır dışlandı "
                  f"→ {len(manifest):,} kesit işlenecek")
    train_cases = set(pd.read_csv(SPLIT_DIR / f"fold{fold}_train.csv")["Case Number"])
    val_cases = set(pd.read_csv(SPLIT_DIR / f"fold{fold}_val.csv")["Case Number"])

    tasks: List[tuple] = []
    for _, row in manifest.iterrows():
        case = int(row["case"])
        if case in train_cases:
            split = "train"
        elif case in val_cases:
            split = "val"
        else:
            continue
        tasks.append((row.to_dict(), split, str(fold_dir), include_val_negatives))

    cpu_count = multiprocessing.cpu_count() or 2
    if platform.system() == "Darwin":
        # macOS: fork güvenli değil, spawn kullan
        n_workers = min(6, cpu_count)
        ctx = multiprocessing.get_context("spawn")
        Executor = ProcessPoolExecutor
        executor_kwargs: dict = {"max_workers": n_workers, "mp_context": ctx}
    else:
        # Linux (Colab): Drive I/O gecikmeleri thread'lerle paralel karşılanır;
        # spawn yükü (her worker ~10s başlangıç) tamamen ortadan kalkar.
        n_workers = min(16, cpu_count * 4)
        Executor = ThreadPoolExecutor
        executor_kwargs = {"max_workers": n_workers}

    with Executor(**executor_kwargs) as executor:
        futures = {executor.submit(_process_manifest_row, t): t for t in tasks}
        for fut in tqdm(as_completed(futures), total=len(tasks), desc=f"YOLO fold{fold}"):
            result = fut.result()
            if result and result.startswith("ERR:"):
                print(f"[skip] {result[4:]}")

    _write_dataset_yaml(fold_dir)
    return fold_dir


def _write_slice_png(row: pd.Series, out_dir: Path) -> Tuple[Path, int, int]:
    import cv2
    from PIL import Image as _PILImage
    dpath = Path(row["dicom_path"])
    ds = read_dicom(dpath)
    hu = dicom_to_hu(ds)
    img = hu_to_three_channel(hu, DEFAULT_WINDOWS)       # float32 ∈ [0,1]
    img = (img * 255.0).astype(np.uint8)
    stem = f"{row['case']}_{row['image_id']}"
    out_path = out_dir / f"{stem}.png"
    # macOS spawn worker'larında cv2.imwrite bazen False döner;
    # PIL ile fallback PNG yazımı tutarlı çalışır.
    ok = cv2.imwrite(str(out_path), img)
    if not ok:
        _PILImage.fromarray(img[:, :, ::-1]).save(str(out_path))
    return out_path, img.shape[0], img.shape[1]


def _write_yolo_label(bboxes_raw: str, h: int, w: int, out: Path) -> None:
    """
    Manifest'in `bboxes` sütununu YOLO formatına çevirir.

    GÜVENLİK GARANTİSİ:
        `bboxes` sütunu yalnızca `preprocessing.build_manifest()` tarafından,
        sadece Type == "Bounding Box" satırlarından doldurulur. Boundary Slice
        satırları Data alanı NaN olduğu için zaten parse edilemez ve bu fonksiyon
        tarafından `nan/boş/eksik` kontrolüyle reddedilir. Yani Boundary Slice
        kaynaklı koordinat ÜRETİLMEZ ve YOLO label'ına ASLA YAZILMAZ.
    """
    seen: set = set()
    lines: List[str] = []
    if bboxes_raw:
        for token in bboxes_raw.split("|"):
            token = token.strip()
            if not token or token.lower() == "nan":
                continue
            parts = token.split(",")
            # Herhangi bir alan nan/boş/eksik ise atla (Boundary Slice'tan
            # gelseydi Data=NaN olur ve burada elenir)
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
            # Geçersiz BB koordinatları
            if x2 <= x1 or y2 <= y1:
                continue
            key = (sid, x1, y1, x2, y2)
            if key in seen:
                continue
            seen.add(key)
            bb = (x1, y1, x2, y2)
            cx, cy, bw, bh = bbox_xyxy_to_yolo(bb, h, w)
            lines.append(f"{sid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
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
# TEST (YARISMA) VERİ HAZIRLIĞI
# ---------------------------------------------------------------------------
def export_yolo_test_dataset(out_root: Path = DET_DATA_DIR) -> Path:
    """
    Yarışma (Test Verisi) setini YOLO inference + değerlendirme için hazırlar.
        out_root/test/
            images/test/*.png
            labels/test/*.txt   ← ground truth (değerlendirme için)

    manifest'teki source='comp' satırları kullanılır; her satırın dicom_path'i
    doğrudan Test Verisi klasörüne işaret eder.
    """
    out_root = Path(out_root)
    test_dir = out_root / "test"
    for sub in ("images/test", "labels/test"):
        p = test_dir / sub
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(SPLIT_DIR / "manifest.csv")
    comp = manifest[
        (manifest["source"] == "comp") &
        (manifest["bboxes"].fillna("").str.strip() != "")
    ].copy()
    print(f"Test seti: {comp['case'].nunique()} vaka, {len(comp):,} bbox'lu kesit")

    tasks = [(row.to_dict(), "test", str(test_dir), True) for _, row in comp.iterrows()]

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
        for fut in tqdm(as_completed(futures), total=len(tasks), desc="YOLO test"):
            result = fut.result()
            if result and result.startswith("ERR:"):
                print(f"[skip] {result[4:]}")

    return test_dir


# ---------------------------------------------------------------------------
# EĞİTİM
# ---------------------------------------------------------------------------
def train_yolo(fold: int, cfg=DEFAULT_DET, project: str = "runs/det") -> Path:
    import torch
    from ultralytics import YOLO

    fold_dir = DET_DATA_DIR / f"fold{fold}"
    if not (fold_dir / "dataset.yaml").exists():
        export_yolo_dataset(fold)

    # Label'ı olan ama görüntüsü eksik dosyaları tespit et
    missing = []
    for split in ("train", "val"):
        for lbl in (fold_dir / "labels" / split).glob("*.txt"):
            img = fold_dir / "images" / split / (lbl.stem + ".png")
            if not img.exists():
                missing.append(img)
    if missing:
        raise FileNotFoundError(
            f"{len(missing)} görüntü eksik (export sırasında cv2.imwrite başarısız olmuş). "
            f"İlk örnek: {missing[0]}\n"
            "export_yolo_dataset() tekrar çalıştırılmalı."
        )

    # MPS → CUDA → CPU öncelik sırası
    if torch.backends.mps.is_available():
        device = "mps"
        n_workers = cfg.workers_mps
    elif torch.cuda.is_available():
        device = "0"
        n_workers = min(cfg.workers_cuda, os.cpu_count() or 4)
    else:
        device = "cpu"
        n_workers = min(cfg.workers_cpu, os.cpu_count() or 2)

    model = YOLO(cfg.model)
    run_name = f"fold{fold}_{Path(cfg.model).stem}"
    model.train(
        data=str(fold_dir / "dataset.yaml"),
        imgsz=cfg.img_size,
        epochs=cfg.epochs,
        batch=cfg.batch_size,
        # ── Augmentation (CT'ye uyarlandı) ─────────────────────────────
        mosaic=cfg.mosaic,          # 0.0 — CT dilimlerini karıştırma
        mixup=cfg.mixup,            # 0.0 — CT'de anlamsız
        fliplr=cfg.fliplr,          # 0.0 — anatomi simetrisi yok
        flipud=cfg.flipud,          # 0.0
        hsv_h=cfg.hsv_h,            # 0.0 — CT grayscale
        hsv_s=cfg.hsv_s,            # 0.0 — CT grayscale
        hsv_v=cfg.hsv_v,            # 0.4 — hafif parlaklık varyasyonu
        degrees=cfg.degrees,        # ±10° — CT dilim açı varyasyonu
        erasing=cfg.erasing,        # 0.1 — küçük lezyonları silmemek için düşük
        copy_paste=cfg.copy_paste,  # 0.3 — nadir sınıf recall artışı
        # ── Kayıp ağırlıkları ──────────────────────────────────────────
        cls=cfg.cls_loss,           # 0.3 — düşük cls baskısı → yüksek recall
        # ── Optimizasyon ───────────────────────────────────────────────
        lr0=cfg.lr0,
        lrf=cfg.lrf,
        weight_decay=cfg.weight_decay,
        # ── Genel ──────────────────────────────────────────────────────
        project=project,
        name=run_name,
        seed=42,
        deterministic=False,
        close_mosaic=0,
        patience=cfg.patience,
        device=device,
        workers=n_workers,
        cache=False,
        amp=True,
    )
    return Path(model.trainer.save_dir) / "weights" / "best.pt"


# ---------------------------------------------------------------------------
# İNFERANS + 3B POST-PROCESSING
# ---------------------------------------------------------------------------
def predict_volume(weights: Path,
                   case_dir: Path,
                   conf: float = 0.2,
                   min_slice_run: int = 3) -> pd.DataFrame:
    """
    Bir vakadaki tüm kesitlerde YOLO çıkarımı yapar ve **sadece ardışık
    `min_slice_run` kesit boyunca süregelen tespitleri** tutar.
    Bu, bağımsız tek-kesitlik false-positive'leri büyük ölçüde süzer.
    """
    from ultralytics import YOLO
    model = YOLO(str(weights))
    dcm_paths = sorted(p for p in case_dir.iterdir() if p.suffix.lower() == ".dcm")

    all_rows = []
    for p in tqdm(dcm_paths, desc=f"predict {case_dir.name}"):
        ds = read_dicom(p)
        hu = dicom_to_hu(ds)
        img = (hu_to_three_channel(hu, DEFAULT_WINDOWS) * 255).astype(np.uint8)
        res = model.predict(img, conf=conf, verbose=False)[0]
        for box, score, cls in zip(res.boxes.xyxy.cpu().numpy(),
                                   res.boxes.conf.cpu().numpy(),
                                   res.boxes.cls.cpu().numpy()):
            all_rows.append({
                "case": case_dir.name,
                "image_id": int(p.stem),
                "class": int(cls),
                "score": float(score),
                "x1": float(box[0]), "y1": float(box[1]),
                "x2": float(box[2]), "y2": float(box[3]),
            })

    df = pd.DataFrame(all_rows)
    if df.empty or min_slice_run <= 1:
        return df

    # Ardışık kesit süreklilik filtresi (sınıf başına IoU tabanlı eşleştirme)
    filt = []
    df = df.sort_values(["class", "image_id"]).reset_index(drop=True)
    for cls, grp in df.groupby("class"):
        grp = grp.reset_index(drop=True)
        kept = [False] * len(grp)
        for i, row in grp.iterrows():
            run = 1
            j = i + 1
            while j < len(grp) and grp.iloc[j]["image_id"] - grp.iloc[j - 1]["image_id"] <= 2:
                if _iou(row, grp.iloc[j]) > 0.3:
                    run += 1
                    j += 1
                else:
                    break
            if run >= min_slice_run:
                for k in range(i, i + run):
                    kept[k] = True
        filt.append(grp[kept])
    return pd.concat(filt, ignore_index=True) if filt else df.iloc[0:0]


def _iou(a, b) -> float:
    ax1, ay1, ax2, ay2 = a["x1"], a["y1"], a["x2"], a["y2"]
    bx1, by1, bx2, by2 = b["x1"], b["y1"], b["x2"], b["y2"]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    ub = max(0.0, (bx2 - bx1) * (by2 - by1))
    return inter / max(ua + ub - inter, 1e-6)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["export", "train"])
    ap.add_argument("--fold", type=int, default=0)
    args = ap.parse_args()

    if args.step == "export":
        d = export_yolo_dataset(args.fold)
        print("YOLO dataset hazır:", d)
    elif args.step == "train":
        w = train_yolo(args.fold)
        print("YOLO best weights:", w)


if __name__ == "__main__":
    main()
