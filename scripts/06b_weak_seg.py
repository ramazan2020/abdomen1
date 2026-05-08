"""BB annotasyonları + TotalSegmentator ile weakly supervised 3D hastalık maskesi üretir."""
import argparse
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.weak_seg import generate_weak_masks

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="Debug: sadece N vaka işlensin")
    ap.add_argument("--no-fast", action="store_true",
                    help="TotalSegmentator --fast bayrağını kapat")
    ap.add_argument("--device", type=str, default=None,
                    help="mps | gpu | cpu (varsayılan: otomatik)")
    ap.add_argument("--workers", type=int, default=4,
                    help="DICOM→NIfTI paralel worker sayısı")
    args = ap.parse_args()
    generate_weak_masks(limit=args.limit,
                        totalseg_fast=not args.no_fast,
                        device=args.device,
                        n_dicom_workers=args.workers)
