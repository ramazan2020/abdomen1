"""Bilgi.xlsx (manifest.csv) annotasyonlarini tasinabilir bir ZIP'e aktar.

Zip icindeki `annotations.json` dosyasi, her annotasyon icin webapp'in
kullandigi 0-bazli z-sirali `webapp_image_id`'yi ONCEDEN COZUMLER — yani
import sirasinda orijinal DICOM dizinine gerek kalmaz.

Buyuk resim: bu ZIP baska bir makineye/ortama tasindi mi, sadece
`import_annotation_zip.py` ile webapp'e yuklenebilir.

Cikti formati (annotations.json icinde):
  {
    "version": "1.0",
    "source": "train",          # "train" | "comp"
    "cases": [
      {
        "case_num": "20001",
        "prefix": "T",          # manifest'teki T_ / C_ on eki
        "annotations": [
          {
            "webapp_image_id": 12,    # z-sirali 0-bazli index (ingest ile ayni)
            "original_image_id": 100007,  # DICOM dosya adi koku (referans)
            "class_id": 1,
            "class_name": "kidney_ureter_stone",
            "geometry_type": "bbox",
            "geometry": {"x1": 251, "y1": 290, "x2": 262, "y2": 302}
          }
        ]
      }
    ]
  }

Kullanim:
    python webapp/scripts/make_annotation_zip.py
    python webapp/scripts/make_annotation_zip.py --source comp --cases 20001 20002
    python webapp/scripts/make_annotation_zip.py --out D:/tmp/egitim_ann.zip
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pydicom

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from src.config import EGITIM_DIR, SPLIT_DIR, SUPER_CLASSES, YARISMA_DIR  # noqa: E402


# ---------------------------------------------------------------------------
# z-siralama eslemesi (import_annotations.py ile ayni mantik)
# ---------------------------------------------------------------------------
def build_z_mapping(case_dir: Path) -> dict[int, int]:
    dcm_paths = [p for p in case_dir.glob("*.dcm") if not p.name.startswith("._")]
    if not dcm_paths:
        raise FileNotFoundError(f"DICOM bulunamadi: {case_dir}")
    items: list[tuple[float, int]] = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        for p in dcm_paths:
            try:
                ds = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
                z = float(ds.ImagePositionPatient[2]) if hasattr(ds, "ImagePositionPatient") else 0.0
            except Exception:
                z = 0.0
            items.append((z, int(p.stem)))
    items.sort(key=lambda t: t[0])
    return {orig_stem: idx for idx, (_, orig_stem) in enumerate(items)}


# ---------------------------------------------------------------------------
# bbox string'den dict'e
# ---------------------------------------------------------------------------
def parse_bboxes(bboxes_str: str) -> list[dict]:
    if not bboxes_str or (isinstance(bboxes_str, float) and str(bboxes_str) == "nan"):
        return []
    result = []
    for part in str(bboxes_str).split("|"):
        tokens = [t.strip() for t in part.split(",")]
        if len(tokens) != 5:
            continue
        try:
            class_id, x1, y1, x2, y2 = map(int, tokens)
            result.append({"class_id": class_id, "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        except ValueError:
            continue
    return result


# ---------------------------------------------------------------------------
# Tek bir case icin annotation listesi olustur
# ---------------------------------------------------------------------------
def extract_case_annotations(
    case_num: str,
    prefix: str,           # "T" veya "C"
    case_dir: Path,
    manifest_df: pd.DataFrame,
) -> list[dict]:
    case_key = f"{prefix}_{case_num}"
    rows = manifest_df[(manifest_df["case"] == case_key) & (manifest_df["n_bbox_anns"] > 0)]
    if rows.empty:
        return []

    z_map = build_z_mapping(case_dir)
    result = []

    for _, row in rows.iterrows():
        orig_id = int(row["image_id"])
        webapp_id = z_map.get(orig_id)
        if webapp_id is None:
            continue

        for bbox in parse_bboxes(row["bboxes"]):
            class_name = SUPER_CLASSES[bbox["class_id"]] if bbox["class_id"] < len(SUPER_CLASSES) else str(bbox["class_id"])
            result.append({
                "webapp_image_id": webapp_id,
                "original_image_id": orig_id,
                "class_id": bbox["class_id"],
                "class_name": class_name,
                "geometry_type": "bbox",
                "geometry": {"x1": bbox["x1"], "y1": bbox["y1"], "x2": bbox["x2"], "y2": bbox["y2"]},
            })

    return result


# ---------------------------------------------------------------------------
# Ana mantik
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--cases", nargs="*", default=[str(i) for i in range(20001, 20006)],
        help="Case numaralari (varsayilan: 20001-20005)",
    )
    parser.add_argument(
        "--source", choices=["train", "comp", "auto"], default="train",
        help="train=Egitim (T_), comp=Test/Yarisma (C_), auto=her ikisi",
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path(__file__).resolve().parent / "sample_zips" / "annotations.zip",
        help="Cikti zip yolu",
    )
    parser.add_argument(
        "--manifest", type=Path, default=SPLIT_DIR / "manifest.csv",
        help="Manifest CSV yolu",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        raise SystemExit(f"manifest.csv bulunamadi: {args.manifest}")

    manifest_df = pd.read_csv(args.manifest)
    print(f"Manifest: {len(manifest_df)} satir")

    # Hangi prefix + dizin kombinasyonlarini dene
    def _candidates(case_num: str) -> list[tuple[str, Path]]:
        cands = []
        if args.source in ("train", "auto"):
            cands.append(("T", EGITIM_DIR / case_num))
        if args.source in ("comp", "auto"):
            cands.append(("C", YARISMA_DIR / case_num))
        return cands

    payload_cases = []
    total_ann = 0

    for case_num in args.cases:
        for prefix, case_dir in _candidates(case_num):
            if not case_dir.exists():
                continue
            annotations = extract_case_annotations(case_num, prefix, case_dir, manifest_df)
            if not annotations and args.source == "auto":
                continue   # auto modda annotasyonu olani bul
            payload_cases.append({
                "case_num": case_num,
                "prefix": prefix,
                "annotations": annotations,
            })
            total_ann += len(annotations)
            print(f"  {prefix}_{case_num}: {len(annotations)} annotasyon")
            break  # bu case icin eslesme bulundu

    if not payload_cases:
        raise SystemExit("Hicbir case icin annotation bulunamadi.")

    output = {
        "version": "1.0",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": args.source,
        "total_annotations": total_ann,
        "cases": payload_cases,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("annotations.json", json.dumps(output, ensure_ascii=False, indent=2))

    size_kb = args.out.stat().st_size / 1024
    print(f"\nOlusturuldu: {args.out}  ({size_kb:.1f} KB)")
    print(f"  Toplam case: {len(payload_cases)}  |  Toplam annotation: {total_ann}")
    print("Import icin: python webapp/scripts/import_annotation_zip.py --zip <yol>")


if __name__ == "__main__":
    main()
