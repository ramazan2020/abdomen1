"""Bilgi.xlsx kaynaklı (manifest.csv) annotasyonları webapp'e aktarır.

Hem Egitim (T_ prefix) hem Yarısma/Test (C_ prefix) case'lerini destekler.
  T_20001 -> Egitim Verisi/20001/   (kaynak: train)
  C_20001 -> Test Verisi/20001/     (kaynak: comp  — test olarak kullanılabilir)

`make_sample_zips.py` ile oluşturulan zip'ler yüklenip ingest tamamlandıktan
sonra çalıştırılır. Aynı case'in Bilgi.xlsx/manifest.csv'deki gerçek bbox
annotasyonlarını POST /cases/{id}/annotations ile webapp DB'ye yazar.

Temel fikir — iki sistem arasında image_id eslemesi:
  Bilgi.xlsx / manifest.csv: image_id = DICOM dosya adi koku (orn. 100007)
  Webapp ingest             : image_id = 0-bazli z-sirali index
  Esleme: case dizinindeki .dcm dosyalari z-konumuna gore siranir.

Kullanim:
    python webapp/scripts/import_annotations.py                     # T_ (Egitim)
    python webapp/scripts/import_annotations.py --source comp       # C_ (Test)
    python webapp/scripts/import_annotations.py --source auto       # her ikisi
    python webapp/scripts/import_annotations.py --cases 20001 20002
    python webapp/scripts/import_annotations.py --email admin@ex.com --password pw
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import pydicom

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from src.config import EGITIM_DIR, YARISMA_DIR, SPLIT_DIR  # noqa: E402


# ---------------------------------------------------------------------------
# Yardımcı: REST API çağrıları (stdlib urllib, `requests` bağımlılığı yok)
# ---------------------------------------------------------------------------
class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base = base_url.rstrip("/")
        self._token = token

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        if extra:
            h.update(extra)
        return h

    def _request(self, method: str, path: str, data: Any = None) -> Any:
        url = f"{self.base}{path}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method, headers=self._headers())
        try:
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {e.read().decode()}") from e

    def login(self, email: str, password: str) -> None:
        form = urllib.parse.urlencode({"username": email, "password": password}).encode()
        req = urllib.request.Request(
            f"{self.base}/auth/login",
            data=form,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req) as resp:
            self._token = json.loads(resp.read())["access_token"]

    def get_cases(self) -> list[dict]:
        return self._request("GET", "/cases")

    def post_annotation(self, case_id: str, payload: dict) -> dict:
        return self._request("POST", f"/cases/{case_id}/annotations", payload)


# ---------------------------------------------------------------------------
# Z-sıralama eşlemesi: orijinal dosya adı kökü ->webapp image_id (0 tabanlı)
# ---------------------------------------------------------------------------
def build_z_mapping(case_dir: Path) -> dict[int, int]:
    """
    case_dir (ör. Egitim Verisi/20001/) altındaki .dcm dosyalarını webapp
    ingest ile *aynı mantıkla* z-konumuna göre sıralar ve:
        {orijinal_stem_int: webapp_image_id} sözlüğü döner.
    """
    dcm_paths = [
        p for p in case_dir.glob("*.dcm")
        if not p.name.startswith("._")
    ]
    if not dcm_paths:
        raise FileNotFoundError(f"DICOM bulunamadı: {case_dir}")

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
    return {orig_stem: webapp_idx for webapp_idx, (_, orig_stem) in enumerate(items)}


# ---------------------------------------------------------------------------
# Manifest'ten annotasyon satırlarını çözümle
# ---------------------------------------------------------------------------
def parse_bboxes(bboxes_str: str) -> list[dict]:
    """
    "1,251,290,262,302|1,251,291,261,301" ->[{"class_id":1, "x1":251, ...}, ...]
    """
    if not bboxes_str or (isinstance(bboxes_str, float)):
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
# Ana logic
# ---------------------------------------------------------------------------
def find_webapp_case(cases: list[dict], case_key: str) -> dict | None:
    """
    Webapp case listesinde case_label içinde TAM prefix'li anahtari arar
    (örn. "T_20001"). Bilerek çıplak case numarası (sadece "20001") ile
    eşleştirme YAPILMAZ — aynı numara hem Egitim hem Test setinde farklı
    vakalara karşılık gelebildiğinden (T_20001 != C_20001) bu karışıklığı
    önler. Webapp'e yüklerken case_label'ı zip dosya adıyla aynı (örn.
    "T_20001") tutmanız gerekir.
    """
    for c in cases:
        label = c.get("case_label") or ""
        if case_key in label:
            return c
    return None


def _resolve_case(case_num: str, source: str, manifest_df: pd.DataFrame) -> tuple[str, Path] | None:
    """
    case_num için (manifest_key, case_dir) ikilisini döner.

    source="train" -> T_ + EGITIM_DIR
    source="comp"  -> C_ + YARISMA_DIR
    source="auto"  -> her ikisini dener, annotasyonu olan tercih edilir;
                      yoksa kaynak dizine gore T_ oncelikli.
    """
    candidates: list[tuple[str, Path]] = []
    if source in ("train", "auto"):
        candidates.append((f"T_{case_num}", EGITIM_DIR / case_num))
    if source in ("comp", "auto"):
        candidates.append((f"C_{case_num}", YARISMA_DIR / case_num))

    if not candidates:
        return None

    # annotasyonu olan varsa onu sec; yoksa dizini var olanı döndür
    for key, cdir in candidates:
        has_ann = not manifest_df[
            (manifest_df["case"] == key) & (manifest_df["n_bbox_anns"] > 0)
        ].empty
        if has_ann and cdir.exists():
            return key, cdir

    # annotasyon yoksa dizini var olan ilk aday
    for key, cdir in candidates:
        if cdir.exists():
            return key, cdir

    return None


def import_case_annotations(
    api: ApiClient,
    case_num: str,
    case_key: str,
    case_dir: Path,
    webapp_case: dict,
    manifest_df: pd.DataFrame,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Tek bir case için annotasyonları içe aktarır. (gönderilen, atlatılan) döner."""
    prefix = "T" if case_key.startswith("T_") else "C"
    rows = manifest_df[
        (manifest_df["case"] == case_key) & (manifest_df["n_bbox_anns"] > 0)
    ]
    if rows.empty:
        print(f"  [{case_num}] ({prefix}_) Bilgi.xlsx'te bbox annotasyonu yok -- atlanıyor")
        return 0, 0

    # z-eşleme: orijinal DICOM dosya adı -> webapp image_id (0 tabanlı)
    z_map = build_z_mapping(case_dir)

    sent = skipped = 0
    webapp_case_id = webapp_case["id"]
    print(f"  [{case_num}] ({prefix}_) {len(rows)} annotasyonlu dilim -> webapp case {webapp_case_id}")

    for _, row in rows.iterrows():
        orig_img_id = int(row["image_id"])         # Bilgi.xlsx image_id = dosya adı kökü
        webapp_img_id = z_map.get(orig_img_id)

        if webapp_img_id is None:
            print(f"    [!] {case_num}/{orig_img_id}.dcm z-eslemede bulunamadi -- atlanıyor")
            skipped += 1
            continue

        bboxes = parse_bboxes(row["bboxes"])
        for bbox in bboxes:
            payload = {
                "image_id": webapp_img_id,
                "class_type": "lesion",
                "class_id": bbox["class_id"],
                "geometry_type": "bbox",
                "geometry": {
                    "x1": bbox["x1"], "y1": bbox["y1"],
                    "x2": bbox["x2"], "y2": bbox["y2"],
                },
            }
            if dry_run:
                print(f"    [dry-run] case={case_num} orig_img={orig_img_id} "
                      f"webapp_img={webapp_img_id} cls={bbox['class_id']} "
                      f"bbox=({bbox['x1']},{bbox['y1']},{bbox['x2']},{bbox['y2']})")
                sent += 1
            else:
                try:
                    api.post_annotation(webapp_case_id, payload)
                    sent += 1
                except RuntimeError as e:
                    print(f"    [X] Annotasyon gonderilemedi: {e}")
                    skipped += 1

    return sent, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--cases", nargs="*", default=[str(i) for i in range(20001, 20006)],
        help="Case numaraları (varsayılan: 20001-20005)",
    )
    parser.add_argument(
        "--source", choices=["train", "comp", "auto"], default="train",
        help=(
            "Kaynak veri seti:\n"
            "  train = Egitim Verisi/  (T_ prefix, varsayilan)\n"
            "  comp  = Test Verisi/    (C_ prefix, yar isma/test seti)\n"
            "  auto  = her ikisini dener, annotasyonu olani secer"
        ),
    )
    parser.add_argument("--api", default="http://localhost:8000/api/v1", help="Backend API kok URL")
    parser.add_argument("--email", default="doktor@example.com")
    parser.add_argument("--password", default="doktor123")
    parser.add_argument(
        "--manifest", type=Path, default=SPLIT_DIR / "manifest.csv",
        help=f"Manifest CSV yolu (varsayilan: {SPLIT_DIR / 'manifest.csv'})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="API'ye gercekten POST etmeden, gonderilecek annotasyonlari yazdirir",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        raise SystemExit(
            f"manifest.csv bulunamadi: {args.manifest}\n"
            "Once 'python -m src.preprocessing manifest' komutuyla manifest olusturun."
        )

    manifest_df = pd.read_csv(args.manifest)
    src_label = {"train": "Egitim (T_)", "comp": "Test/Yarisma (C_)", "auto": "Otomatik (T_+C_)"}
    print(f"Manifest: {len(manifest_df)} satir yuklendi  |  kaynak: {src_label[args.source]}")

    api = ApiClient(args.api)
    print(f"Giris yapiliyor: {args.email} -> {args.api}")
    if not args.dry_run:
        try:
            api.login(args.email, args.password)
        except Exception as e:
            raise SystemExit(f"Auth hatasi: {e}") from e

    cases_list = api.get_cases() if not args.dry_run else []

    total_sent = total_skipped = 0
    for case_num in args.cases:
        resolved = _resolve_case(case_num, args.source, manifest_df)
        if resolved is None:
            print(f"  [{case_num}] Case dizini bulunamadi (source={args.source}) -- atlanıyor")
            continue
        case_key, case_dir = resolved

        webapp_case = find_webapp_case(cases_list, case_key) if not args.dry_run else {"id": "dry-run"}
        if webapp_case is None:
            print(f"  [{case_key}] Webapp'te esleyen case bulunamadi "
                  f"(case_label '{case_key}' icermeli) -- once zip'i yukleyin")
            continue
        sent, skipped = import_case_annotations(
            api, case_num, case_key, case_dir, webapp_case, manifest_df, args.dry_run
        )
        total_sent += sent
        total_skipped += skipped

    print(f"\nTamamlandi: {total_sent} annotasyon gonderildi, {total_skipped} atlatildi.")


if __name__ == "__main__":
    main()
