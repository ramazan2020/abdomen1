"""Vaka bazlı 5-fold + hold-out split üretir."""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.splits import make_splits


if __name__ == "__main__":
    paths = make_splits()
    for k, v in paths.items():
        print(f"{k}: {v}")
