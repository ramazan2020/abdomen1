"""Manifest üret ve sınıflandırma için 3-kanallı NPZ kesitleri kaydet."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.preprocessing import build_manifest, export_slices


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--negatives", type=int, default=0,
                    help="vaka başına rastgele negatif kesit sayısı")
    ap.add_argument("--only", choices=["manifest", "export", "all"], default="manifest")
    args = ap.parse_args()

    if args.only in ("manifest", "all"):
        build_manifest()
    if args.only in ("export", "all"):
        export_slices(include_negative_sampling=args.negatives)
