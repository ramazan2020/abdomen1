"""TotalSegmentator ile 6 anatomik organ için pseudo-label üretir."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.segmentation import generate_pseudo_labels


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Debug için sadece N vaka işlensin")
    args = ap.parse_args()
    generate_pseudo_labels(limit=args.limit)
