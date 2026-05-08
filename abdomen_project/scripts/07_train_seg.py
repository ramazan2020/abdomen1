"""nnU-Net v2 iteratif self-training döngüsünü çalıştırır."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.config import DEFAULT_SEG
from src.segmentation import self_training_loop


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=DEFAULT_SEG.pseudo_iterations)
    args = ap.parse_args()
    self_training_loop(iterations=args.iters)
