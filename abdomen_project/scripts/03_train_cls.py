"""Bir fold üzerinde ConvNeXt multi-label sınıflandırıcı eğitir."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_CLS
from src.train_cls import train_one_fold


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--epochs", type=int, default=DEFAULT_CLS.epochs)
    ap.add_argument("--batch", type=int, default=DEFAULT_CLS.batch_size)
    ap.add_argument("--backbone", type=str, default=DEFAULT_CLS.backbone)
    args = ap.parse_args()

    cfg = DEFAULT_CLS
    cfg.epochs = args.epochs
    cfg.batch_size = args.batch
    cfg.backbone = args.backbone

    best = train_one_fold(args.fold, cfg)
    print("BEST:", best)
