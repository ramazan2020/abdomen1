"""Hazırlanmış fold üzerinde YOLOv8 eğitir."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.detection import train_yolo


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    args = ap.parse_args()
    w = train_yolo(args.fold)
    print("YOLO best weights:", w)
