"""Bir fold için YOLOv8 veri setini hazırlar (images/ + labels/ + dataset.yaml)."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.detection import export_yolo_dataset


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", type=int, default=0)
    args = ap.parse_args()
    path = export_yolo_dataset(args.fold)
    print("Hazır:", path)
