"""
Multi-label sınıflandırıcı (ConvNeXt-Base) eğitimi.
Tek fold mantığı — çağıran script tüm foldları sırayla çalıştırabilir.

MPS (Apple Silicon) optimizasyonları:
  • pin_memory=False  (MPS desteklemiyor)
  • num_workers=2     (DataLoader fork sorunu önlemek için)
  • autocast("mps")   (PyTorch 2.2+ destekli, bfloat16)
  • torch.mps.empty_cache() her epoch sonrası
  • GradScaler devre dışı (MPS amp scaler yok)
"""
from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import average_precision_score, f1_score
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from torch.utils.data import DataLoader, WeightedRandomSampler
from tqdm import tqdm

from .device_utils import get_device

try:
    import timm
except ImportError:                     # pragma: no cover
    timm = None

try:
    from torch.utils.tensorboard import SummaryWriter
    _TB_AVAILABLE = True
except ImportError:
    _TB_AVAILABLE = False

from .config import CKPT_DIR, DEFAULT_CLS, LOG_DIR, SUPER_CLASSES
from .datasets import SliceMultiLabelDataset, load_manifest
from .losses import FocalBCE, compute_class_balanced_alpha
from .splits import load_fold


# ---------------------------------------------------------------------------
# YARDIMCI: autocast bağlamı
# ---------------------------------------------------------------------------
def _autocast_ctx(device: torch.device):
    """Device'a göre uygun autocast bağlamını döner."""
    if device.type == "cuda":
        return torch.autocast("cuda", dtype=torch.bfloat16)
    elif device.type == "mps":
        # PyTorch 2.2+ MPS autocast destekler
        return torch.autocast("mps", dtype=torch.bfloat16)
    else:
        return torch.autocast("cpu", enabled=False)


# ---------------------------------------------------------------------------
# MODEL
# ---------------------------------------------------------------------------
def build_model(cfg=DEFAULT_CLS) -> nn.Module:
    if timm is None:
        raise RuntimeError("timm kurulu değil; `pip install timm`")
    model = timm.create_model(
        cfg.backbone,
        pretrained=True,
        num_classes=cfg.num_classes,
        in_chans=3,
    )
    return model


# ---------------------------------------------------------------------------
# METRİK
# ---------------------------------------------------------------------------
@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device,
             thresholds: Optional[np.ndarray] = None) -> Dict:
    model.eval()
    all_logits, all_labels = [], []
    for batch in tqdm(loader, desc="  val", leave=False, unit="bat"):
        with _autocast_ctx(device):
            logits = model(batch["image"].to(device))
        all_logits.append(logits.float().sigmoid().cpu().numpy())
        all_labels.append(batch["labels"].numpy())
    y_pred = np.concatenate(all_logits)
    y_true = np.concatenate(all_labels)

    if thresholds is None:
        thresholds = np.full(y_pred.shape[1], 0.5)
    pred_bin = (y_pred >= thresholds).astype(np.int32)

    metrics = {}
    for i, cls in enumerate(SUPER_CLASSES):
        if y_true[:, i].sum() == 0:
            metrics[f"AP/{cls}"] = float("nan")
            metrics[f"F1/{cls}"] = float("nan")
            continue
        metrics[f"AP/{cls}"] = float(average_precision_score(y_true[:, i], y_pred[:, i]))
        metrics[f"F1/{cls}"] = float(f1_score(y_true[:, i], pred_bin[:, i], zero_division=0))
    metrics["mAP"]     = float(np.nanmean([metrics[f"AP/{c}"] for c in SUPER_CLASSES]))
    metrics["macroF1"] = float(np.nanmean([metrics[f"F1/{c}"] for c in SUPER_CLASSES]))
    return metrics


@torch.no_grad()
def tune_thresholds(model: nn.Module, loader: DataLoader,
                    device: torch.device,
                    n_thresholds: int = 51) -> np.ndarray:
    """Val seti üzerinde sınıf başına F1 maksimize eden sigmoid eşiğini bulur."""
    model.eval()
    all_logits, all_labels = [], []
    for batch in tqdm(loader, desc="  threshold tuning", leave=False, unit="bat"):
        with _autocast_ctx(device):
            logits = model(batch["image"].to(device))
        all_logits.append(logits.float().sigmoid().cpu().numpy())
        all_labels.append(batch["labels"].numpy())
    y_pred = np.concatenate(all_logits)
    y_true = np.concatenate(all_labels)

    n_cls      = y_pred.shape[1]
    thresholds = np.full(n_cls, 0.5)
    candidates = np.linspace(0.05, 0.95, n_thresholds)

    print("  Threshold tuning (val):")
    for c in range(n_cls):
        if y_true[:, c].sum() == 0:
            print(f"    {SUPER_CLASSES[c]:<33} th=0.50  F1=n/a  (no positives)")
            continue
        best_f1, best_th = 0.0, 0.5
        for th in candidates:
            pred_bin = (y_pred[:, c] >= th).astype(np.int32)
            f1 = f1_score(y_true[:, c], pred_bin, zero_division=0)
            if f1 > best_f1:
                best_f1, best_th = f1, th
        thresholds[c] = best_th
        print(f"    {SUPER_CLASSES[c]:<33} th={best_th:.2f}  F1={best_f1:.4f}")

    return thresholds


def _print_metrics_table(metrics: Dict, fold: int, epoch: int) -> None:
    """Per-class AP/F1 tablosunu ekrana yazar."""
    header = f"\n{'Sınıf':<35} {'AP':>7}  {'F1':>7}"
    sep    = "─" * len(header)
    print(sep)
    print(f"  Fold {fold}  Epoch {epoch:02d}  │  mAP={metrics['mAP']:.4f}  macroF1={metrics['macroF1']:.4f}")
    print(header)
    print(sep)
    for cls in SUPER_CLASSES:
        ap = metrics.get(f"AP/{cls}", float("nan"))
        f1 = metrics.get(f"F1/{cls}", float("nan"))
        print(f"  {cls:<33} {ap:>7.4f}  {f1:>7.4f}")
    print(sep)


# ---------------------------------------------------------------------------
# EĞİTİM DÖNGÜSÜ
# ---------------------------------------------------------------------------
def train_one_fold(fold: int, cfg=DEFAULT_CLS) -> Dict:
    # M5 MPS: yüksek watermark OOM'u önler; matmul hızlandırır
    os.environ.setdefault("PYTORCH_MPS_HIGH_WATERMARK_RATIO", "0.0")
    torch.set_float32_matmul_precision("high")

    device = get_device(verbose=True)

    # ── DataLoader ayarları ──────────────────────────────────────────────
    pin     = device.type == "cuda"                       # MPS desteklemez
    if device.type == "mps":
        # spawn context → MPS fork sorununu önler; M5 Pro/Max için 6 worker
        n_work  = min(6, os.cpu_count() or 4)
        mp_ctx  = "spawn"
    elif device.type == "cuda":
        n_work  = min(8, os.cpu_count() or 4)
        mp_ctx  = None
    else:
        n_work  = min(4, os.cpu_count() or 2)
        mp_ctx  = None

    persistent = n_work > 0
    prefetch   = 4 if n_work > 0 else None

    train_cases = load_fold(fold, "train")
    val_cases   = load_fold(fold, "val")

    train_ds = SliceMultiLabelDataset(train_cases, input_size=cfg.input_size)
    val_ds   = SliceMultiLabelDataset(val_cases,   input_size=cfg.input_size)

    # ── Class-balanced loss + sampler ────────────────────────────────────
    mani       = load_manifest(train_cases)
    pos_counts = _count_positives_from_manifest(mani)
    alpha      = compute_class_balanced_alpha(pos_counts, total=len(mani))
    print(f"[fold {fold}] pos counts: {pos_counts}")
    print(f"[fold {fold}] alpha     : {[f'{a:.3f}' for a in alpha.tolist()]}")

    if cfg.use_weighted_sampler:
        slice_weights = _compute_slice_weights(train_ds, mani, pos_counts)
        sampler = WeightedRandomSampler(
            weights=slice_weights,
            num_samples=len(train_ds),
            replacement=True,
        )
        print(f"[fold {fold}] WeightedRandomSampler aktif  "
              f"(min={slice_weights.min():.2f} max={slice_weights.max():.2f} "
              f"mean={slice_weights.mean():.2f})")
        train_loader = DataLoader(
            train_ds, batch_size=cfg.batch_size, sampler=sampler,
            num_workers=n_work, pin_memory=pin, drop_last=True,
            multiprocessing_context=mp_ctx,
            persistent_workers=persistent, prefetch_factor=prefetch,
        )
    else:
        train_loader = DataLoader(
            train_ds, batch_size=cfg.batch_size, shuffle=True,
            num_workers=n_work, pin_memory=pin, drop_last=True,
            multiprocessing_context=mp_ctx,
            persistent_workers=persistent, prefetch_factor=prefetch,
        )

    val_loader = DataLoader(
        val_ds, batch_size=cfg.batch_size, shuffle=False,
        num_workers=n_work, pin_memory=pin,
        multiprocessing_context=mp_ctx,
        persistent_workers=persistent, prefetch_factor=prefetch,
    )

    # ── Model ────────────────────────────────────────────────────────────
    model = build_model(cfg).to(device)
    criterion = FocalBCE(gamma=cfg.focal_gamma, alpha=alpha) if cfg.use_focal \
                else nn.BCEWithLogitsLoss()
    optim = AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    # ── Scheduler: Warmup → CosineAnnealing ─────────────────────────────
    warmup_epochs = max(1, cfg.warmup_epochs)
    cosine_epochs = max(1, cfg.epochs - warmup_epochs)
    warmup_sched  = LinearLR(optim,
                             start_factor=1e-3,
                             end_factor=1.0,
                             total_iters=warmup_epochs)
    cosine_sched  = CosineAnnealingLR(optim, T_max=cosine_epochs, eta_min=cfg.lr * 1e-3)
    sched = SequentialLR(optim,
                         schedulers=[warmup_sched, cosine_sched],
                         milestones=[warmup_epochs])

    # ── GradScaler (sadece CUDA) ─────────────────────────────────────────
    use_scaler = device.type == "cuda"
    if hasattr(torch.amp, "GradScaler"):
        scaler = torch.amp.GradScaler("cuda", enabled=use_scaler)
    else:
        scaler = torch.cuda.amp.GradScaler(enabled=use_scaler)

    # ── Gradient accumulation ────────────────────────────────────────────
    accum = max(1, cfg.accum_steps)

    # ── TensorBoard ──────────────────────────────────────────────────────
    tb_writer: Optional[object] = None
    if _TB_AVAILABLE:
        tb_dir = LOG_DIR / "tb" / f"cls_fold{fold}"
        tb_dir.mkdir(parents=True, exist_ok=True)
        tb_writer = SummaryWriter(str(tb_dir))
        print(f"📊 TensorBoard log: {tb_dir}")
        print(f"   tensorboard --logdir {LOG_DIR / 'tb'}")

    # ── Checkpoints ──────────────────────────────────────────────────────
    ckpt_dir = CKPT_DIR / f"cls_fold{fold}"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    best    = {"mAP": -1.0, "epoch": -1}
    log_rows: List[Dict] = []
    steps_per_epoch = len(train_loader)
    total_steps     = cfg.epochs * steps_per_epoch

    print(f"\n{'='*60}")
    print(f"  EĞİTİM BAŞLIYOR  │  Fold {fold}  │  {cfg.epochs} epoch")
    print(f"  Backbone  : {cfg.backbone}")
    print(f"  Device    : {device}  (workers={n_work}, ctx={mp_ctx or 'fork'}, pin={pin}, prefetch={prefetch})")
    print(f"  Batch     : {cfg.batch_size}  (accum={accum} → eff={cfg.batch_size*accum})")
    print(f"  Warmup    : {warmup_epochs} epoch → CosineAnnealing {cosine_epochs} epoch")
    print(f"  LR        : {cfg.lr}  →  {cfg.lr*1e-3:.2e}")
    print(f"  Train/Val : {len(train_ds)}/{len(val_ds)} slice")
    print(f"{'='*60}\n")

    t_train_start = time.time()

    for epoch in range(cfg.epochs):
        model.train()
        t0       = time.time()
        running  = 0.0
        optim.zero_grad(set_to_none=True)

        # ── epoch-level ilerleme çubuğu ───────────────────────────────
        pbar = tqdm(
            train_loader,
            desc=f"[F{fold}] Ep {epoch+1:02d}/{cfg.epochs}",
            unit="bat",
            dynamic_ncols=True,
            leave=True,
        )

        for step, batch in enumerate(pbar):
            imgs    = batch["image"].to(device, non_blocking=True)
            targets = batch["labels"].to(device, non_blocking=True)

            with _autocast_ctx(device):
                logits = model(imgs)
                loss   = criterion(logits, targets) / accum   # normalize

            if use_scaler:
                scaler.scale(loss).backward()
            else:
                loss.backward()

            # accumulate
            if (step + 1) % accum == 0 or (step + 1) == steps_per_epoch:
                if use_scaler:
                    scaler.unscale_(optim)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    scaler.step(optim)
                    scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                    optim.step()
                optim.zero_grad(set_to_none=True)

            running += loss.item() * accum   # gerçek loss

            # tqdm satır bilgisi
            elapsed  = time.time() - t_train_start
            done_s   = epoch * steps_per_epoch + step + 1
            eta_s    = elapsed / done_s * (total_steps - done_s) if done_s > 0 else 0
            cur_lr   = optim.param_groups[0]["lr"]
            pbar.set_postfix({
                "loss": f"{running/(step+1):.4f}",
                "lr"  : f"{cur_lr:.2e}",
                "ETA" : _fmt_eta(eta_s),
            }, refresh=False)

        pbar.close()
        sched.step()
        train_loss = running / steps_per_epoch

        # ── MPS bellek temizleme ──────────────────────────────────────
        if device.type == "mps":
            torch.mps.empty_cache()

        # ── Validation ───────────────────────────────────────────────
        metrics = evaluate(model, val_loader, device)
        epoch_sec = time.time() - t0
        metrics["train_loss"] = train_loss
        metrics["epoch"]      = epoch
        metrics["epoch_sec"]  = epoch_sec
        metrics["lr"]         = optim.param_groups[0]["lr"]
        log_rows.append(metrics)

        # per-class tablo
        _print_metrics_table(metrics, fold, epoch)

        # epoch özeti satırı
        total_elapsed = time.time() - t_train_start
        remaining     = total_elapsed / (epoch + 1) * (cfg.epochs - epoch - 1)
        print(f"  ⏱  Epoch süresi: {epoch_sec:.0f}s  │  "
              f"Toplam: {_fmt_eta(total_elapsed)}  │  "
              f"Kalan: {_fmt_eta(remaining)}")

        # ── TensorBoard ──────────────────────────────────────────────
        if tb_writer is not None:
            tb_writer.add_scalar("loss/train", train_loss, epoch)
            tb_writer.add_scalar("metrics/mAP",     metrics["mAP"],     epoch)
            tb_writer.add_scalar("metrics/macroF1", metrics["macroF1"], epoch)
            tb_writer.add_scalar("lr", metrics["lr"], epoch)
            for cls in SUPER_CLASSES:
                ap = metrics.get(f"AP/{cls}", float("nan"))
                if not math.isnan(ap):
                    tb_writer.add_scalar(f"AP/{cls}", ap, epoch)

        # ── En iyi modeli kaydet ──────────────────────────────────────
        if metrics["mAP"] > best["mAP"]:
            best = {
                "mAP"     : metrics["mAP"],
                "macroF1" : metrics["macroF1"],
                "epoch"   : epoch,
            }
            torch.save({
                "model"  : model.state_dict(),
                "cfg"    : cfg.__dict__,
                "epoch"  : epoch,
                "metrics": metrics,
            }, ckpt_dir / "best.pth")
            print(f"  ✅ Yeni en iyi kaydedildi → mAP={best['mAP']:.4f}")

    # ── Eğitim tamamlandı ─────────────────────────────────────────────
    total_time = time.time() - t_train_start
    print(f"\n{'='*60}")
    print(f"  EĞİTİM TAMAMLANDI  │  Fold {fold}  │  {_fmt_eta(total_time)}")
    print(f"  En iyi  → epoch={best['epoch']:02d}  mAP={best['mAP']:.4f}  macroF1={best['macroF1']:.4f}")
    print(f"{'='*60}\n")

    # ── Threshold tuning (best checkpoint üzerinde) ───────────────────
    _best_ckpt = ckpt_dir / "best.pth"
    if _best_ckpt.exists():
        _state = torch.load(str(_best_ckpt), map_location=device)
        model.load_state_dict(_state["model"])
        print("Threshold tuning için best checkpoint yüklendi.")
    opt_thresholds = tune_thresholds(model, val_loader, device)
    best["thresholds"] = opt_thresholds.tolist()

    # Threshold'ları checkpoint'e ekle ve yeniden kaydet
    if _best_ckpt.exists():
        _state["thresholds"] = opt_thresholds.tolist()
        torch.save(_state, str(_best_ckpt))

    # Tuned threshold ile son val metriklerini logla
    metrics_tuned = evaluate(model, val_loader, device, thresholds=opt_thresholds)
    print(f"\n  mAP (tuned th)     : {metrics_tuned['mAP']:.4f}")
    print(f"  macroF1 (tuned th) : {metrics_tuned['macroF1']:.4f}")
    best["mAP_tuned"]     = metrics_tuned["mAP"]
    best["macroF1_tuned"] = metrics_tuned["macroF1"]

    pd.DataFrame(log_rows).to_csv(LOG_DIR / f"cls_fold{fold}.csv", index=False)
    json.dump(best, open(ckpt_dir / "best_meta.json", "w"), indent=2, default=float)

    if tb_writer is not None:
        tb_writer.add_scalar("metrics/mAP_tuned",     metrics_tuned["mAP"],     cfg.epochs)
        tb_writer.add_scalar("metrics/macroF1_tuned", metrics_tuned["macroF1"], cfg.epochs)
        tb_writer.close()

    return best


# ---------------------------------------------------------------------------
# YARDIMCI
# ---------------------------------------------------------------------------
def _fmt_eta(seconds: float) -> str:
    """Saniyeyi  HH:MM:SS  ya da  Xm Ys  formatına çevirir."""
    s = int(seconds)
    h, remainder = divmod(s, 3600)
    m, sc = divmod(remainder, 60)
    if h:
        return f"{h}s{m:02d}d{sc:02d}s"
    return f"{m}d{sc:02d}s"


def _count_positives_from_manifest(mani: pd.DataFrame) -> list[int]:
    counts = [0] * len(SUPER_CLASSES)
    for s in mani["super_labels"].fillna(""):
        for sid in str(s).split(";"):
            if sid != "":
                counts[int(sid)] += 1
    return counts


def _compute_slice_weights(train_ds: SliceMultiLabelDataset,
                           mani: pd.DataFrame,
                           pos_counts: List[int]) -> torch.Tensor:
    """
    WeightedRandomSampler için kesit başı örnekleme ağırlığı.
    Nadir sınıf içeren kesitler daha sık çekilir.
    Negatif (tüm sınıflar yok) kesitler min_weight=1.0 alır.
    """
    total = len(mani)
    inv_freq = np.array(
        [total / max(c, 1) for c in pos_counts], dtype=np.float64
    )
    inv_freq = inv_freq / inv_freq.mean()   # ortalama ≈ 1

    # (case, image_id) → [cls_ids] lookup
    lookup: Dict[tuple, List[int]] = {}
    for _, row in mani.iterrows():
        sl = str(row.get("super_labels", "")).strip()
        cls_ids = [int(s) for s in sl.split(";") if s.strip()]
        lookup[(row["case"], int(row["image_id"]))] = cls_ids

    weights = np.ones(len(train_ds.files), dtype=np.float64)
    for i, fp in enumerate(train_ds.files):
        parts = fp.stem.rsplit("_", 1)
        if len(parts) == 2:
            case, img_id = parts[0], int(parts[1])
            cls_ids = lookup.get((case, img_id), [])
            if cls_ids:
                weights[i] = max(inv_freq[c] for c in cls_ids)

    return torch.tensor(weights, dtype=torch.double)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold",     type=int,   default=0)
    ap.add_argument("--epochs",   type=int,   default=DEFAULT_CLS.epochs)
    ap.add_argument("--batch",    type=int,   default=DEFAULT_CLS.batch_size)
    ap.add_argument("--backbone", type=str,   default=DEFAULT_CLS.backbone)
    ap.add_argument("--accum",    type=int,   default=DEFAULT_CLS.accum_steps)
    ap.add_argument("--warmup",   type=int,   default=DEFAULT_CLS.warmup_epochs)
    args = ap.parse_args()

    cfg              = DEFAULT_CLS
    cfg.epochs       = args.epochs
    cfg.batch_size   = args.batch
    cfg.backbone     = args.backbone
    cfg.accum_steps  = args.accum
    cfg.warmup_epochs = args.warmup

    best = train_one_fold(args.fold, cfg)
    print("BEST:", best)


if __name__ == "__main__":
    main()
