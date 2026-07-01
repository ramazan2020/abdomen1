"""Gerçek veri setinden örnek DICOM seri zip'leri üretir — webapp'in
`POST /cases/upload` endpoint'ini gerçek verilerle test etmek için.

Bilgi.xlsx iki ayrı sayfadan oluşur ve case numaraları arasında ÇAKIŞMA
olabilir (örn. "20001" hem Egitim hem Test setinde var, ama tamamen farklı
vaka/annotasyonlara karşılık gelir):
    TRAIININGDATA   -> T_ prefix -> Egitim Verisi/{case_id}/{image_id}.dcm
    COMPETITIONDATA -> C_ prefix -> Test Verisi/{case_id}/{image_id}.dcm

Karışmaması için çıktı zip'leri her zaman prefix ile adlandırılır:
    T_20001.zip, C_20001.zip, ...
Bu prefix, webapp'e yüklerken case_label olarak da önerilir ve
import_annotation_zip.py / import_annotations.py ile eşleştirmede
kullanılan TEK kaynak kimliğidir — asla çıplak case numarası kullanılmaz.

Kullanım:
    python webapp/scripts/make_sample_zips.py                       # T_ (Egitim), ilk 5
    python webapp/scripts/make_sample_zips.py --source comp         # C_ (Test/Yarışma)
    python webapp/scripts/make_sample_zips.py --count 5 --max-slices 30
    python webapp/scripts/make_sample_zips.py --cases 20001 20002 20003
    python webapp/scripts/make_sample_zips.py --out D:/tmp/ornek_zipler
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

# repo kökünü sys.path'e ekle (src/ paketini bulabilmek için)
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from src.config import EGITIM_DIR, YARISMA_DIR  # noqa: E402  (sys.path eklendikten sonra import)

_SOURCE_CONFIG = {
    "train": ("T", EGITIM_DIR),
    "comp": ("C", YARISMA_DIR),
}


def list_case_dirs(dataset_dir: Path) -> list[Path]:
    return sorted(
        (p for p in dataset_dir.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.name,
    )


def zip_case(case_dir: Path, out_path: Path, max_slices: int | None) -> int:
    dcm_files = sorted(
        (p for p in case_dir.glob("*.dcm") if not p.name.startswith("._")),
        key=lambda p: p.stem,
    )
    if max_slices is not None:
        dcm_files = dcm_files[:max_slices]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in dcm_files:
            zf.write(p, arcname=p.name)
    return len(dcm_files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--source", choices=["train", "comp"], default="train",
        help="train=Egitim Verisi (T_ prefix, varsayılan), comp=Test Verisi (C_ prefix, yarışma/test seti)",
    )
    parser.add_argument(
        "--src", type=Path, default=None,
        help="Veri seti kök dizinini elle override eder (varsayılan: --source'a göre EGITIM_DIR/YARISMA_DIR)",
    )
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "sample_zips",
        help="Zip'lerin yazılacağı dizin",
    )
    parser.add_argument("--count", type=int, default=5, help="Kaç örnek case zip'lenecek (varsayılan: 5)")
    parser.add_argument(
        "--cases", nargs="*", default=None,
        help="Belirli case numaraları (prefix'siz, örn. --cases 20001 20002) — verilirse --count yok sayılır",
    )
    parser.add_argument(
        "--max-slices", type=int, default=None,
        help="Her case için en fazla kaç dilim zip'lensin (varsayılan: tümü — bazı case'ler 600+ dilim, "
        "yüzlerce MB olabilir; hızlı test için örn. --max-slices 30 verin)",
    )
    args = parser.parse_args()

    prefix, default_src = _SOURCE_CONFIG[args.source]
    src_dir = args.src if args.src is not None else default_src

    if not src_dir.exists():
        raise SystemExit(f"Veri seti dizini bulunamadı: {src_dir}")

    if args.cases:
        case_dirs = [src_dir / c for c in args.cases]
        missing = [c for c in case_dirs if not c.exists()]
        if missing:
            raise SystemExit(f"Bulunamayan case dizin(ler)i: {[str(m) for m in missing]}")
    else:
        all_cases = list_case_dirs(src_dir)
        if not all_cases:
            raise SystemExit(f"{src_dir} altında case dizini bulunamadı")
        case_dirs = all_cases[: args.count]

    print(f"Kaynak  : {src_dir}  (prefix: {prefix}_)")
    print(f"Hedef   : {args.out}")
    print(f"Case'ler: {[f'{prefix}_{c.name}' for c in case_dirs]}")
    if args.max_slices:
        print(f"Her case en fazla {args.max_slices} dilimle sınırlandırılacak")
    print()

    for case_dir in case_dirs:
        prefixed_name = f"{prefix}_{case_dir.name}"
        out_path = args.out / f"{prefixed_name}.zip"
        n = zip_case(case_dir, out_path, args.max_slices)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"  {prefixed_name}: {n} dilim -> {out_path} ({size_mb:.1f} MB)")

    print(f"\nTamamlandı. {len(case_dirs)} zip dosyası '{args.out}' altında.")
    print(
        "Webapp'e yüklerken vaka etiketini (case_label) dosya adıyla AYNI tutun "
        f"(örn. '{prefix}_20001') — annotasyon importu bu etikete göre eşleştirme yapar."
    )


if __name__ == "__main__":
    main()
