"""Annotation ZIP'ini webapp'e import eder.

`make_annotation_zip.py` ile uretilem bir zip dosyasini alip icindeki
`annotations.json` uzerinden webapp'in REST API'sine POST eder.

ZIP icindeki `webapp_image_id` zaten z-siralamasi cozumlenmis sekilde
saklandigi icin import sirasinda orijinal DICOM'a GEREK YOKTUR.
Bu zip baska bir makineye/ortama tasindi mi aynen calisir.

Eslesme: webapp'teki case bulunurken `case_label` alani icinde case
numarasi aranir (orn. "Gercek Vaka 20001" etiketi 20001 ile eslesir).

Kullanim:
    python webapp/scripts/import_annotation_zip.py
    python webapp/scripts/import_annotation_zip.py --zip annotations.zip
    python webapp/scripts/import_annotation_zip.py --dry-run
    python webapp/scripts/import_annotation_zip.py --email admin@ex.com --password pw
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_ZIP = Path(__file__).resolve().parent / "sample_zips" / "annotations.zip"


# ---------------------------------------------------------------------------
# API istemcisi
# ---------------------------------------------------------------------------
class ApiClient:
    def __init__(self, base_url: str, token: str | None = None):
        self.base = base_url.rstrip("/")
        self._token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _request(self, method: str, path: str, data=None):
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
            f"{self.base}/auth/login", data=form, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req) as resp:
            self._token = json.loads(resp.read())["access_token"]

    def get_cases(self) -> list[dict]:
        return self._request("GET", "/cases")

    def post_annotation(self, case_id: str, payload: dict) -> dict:
        return self._request("POST", f"/cases/{case_id}/annotations", payload)


# ---------------------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------------------
def find_webapp_case(cases: list[dict], case_key: str) -> dict | None:
    """case_label içinde TAM prefix'li anahtarı arar (örn. "T_20001") —
    çıplak case numarasıyla eşleştirme yapılmaz (T_20001 != C_20001 olabilir)."""
    for c in cases:
        if case_key in (c.get("case_label") or ""):
            return c
    return None


def read_zip(zip_path: Path) -> dict:
    with zipfile.ZipFile(zip_path, "r") as zf:
        if "annotations.json" not in zf.namelist():
            raise SystemExit(f"ZIP icinde 'annotations.json' bulunamadi: {zip_path}")
        return json.loads(zf.read("annotations.json").decode("utf-8"))


# ---------------------------------------------------------------------------
# Ana mantik
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--zip", type=Path, default=DEFAULT_ZIP, help=f"Annotation ZIP yolu (varsayilan: {DEFAULT_ZIP})")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", default="doktor@example.com")
    parser.add_argument("--password", default="doktor123")
    parser.add_argument("--dry-run", action="store_true", help="API'ye gondermeden yazdirma modu")
    args = parser.parse_args()

    if not args.zip.exists():
        raise SystemExit(f"ZIP bulunamadi: {args.zip}")

    data = read_zip(args.zip)
    print(f"ZIP okundu: {args.zip}")
    print(f"  Versiyon : {data.get('version')}  |  Kaynak: {data.get('source')}  |  Olusturulma: {data.get('created_at')}")
    print(f"  Case     : {len(data['cases'])}  |  Toplam annotation: {data.get('total_annotations', '?')}")
    print()

    api = ApiClient(args.api)
    if not args.dry_run:
        print(f"Giris yapiliyor: {args.email} -> {args.api}")
        try:
            api.login(args.email, args.password)
        except Exception as e:
            raise SystemExit(f"Auth hatasi: {e}") from e

    cases_list = api.get_cases() if not args.dry_run else []

    total_sent = total_skipped = 0

    for case_entry in data["cases"]:
        case_num = case_entry["case_num"]
        prefix = case_entry.get("prefix", "T")
        annotations = case_entry.get("annotations", [])

        if not annotations:
            print(f"  [{prefix}_{case_num}] Annotation yok -- atlaniyor")
            continue

        case_key = f"{prefix}_{case_num}"
        webapp_case = find_webapp_case(cases_list, case_key) if not args.dry_run else {"id": "dry-run"}
        if webapp_case is None:
            print(f"  [{case_key}] Webapp'te esleyen case bulunamadi"
                  f" (case_label '{case_key}' icermeli) -- once zip'i yukleyin")
            total_skipped += len(annotations)
            continue

        case_id = webapp_case["id"]
        print(f"  [{prefix}_{case_num}] {len(annotations)} annotation -> webapp case {case_id}")

        for ann in annotations:
            payload = {
                "image_id": ann["webapp_image_id"],
                "class_type": "lesion",
                "class_id": ann["class_id"],
                "geometry_type": ann["geometry_type"],
                "geometry": ann["geometry"],
            }
            if args.dry_run:
                g = ann["geometry"]
                print(f"    [dry-run] img={ann['webapp_image_id']} cls={ann['class_id']}"
                      f" ({ann.get('class_name','?')}) bbox=({g['x1']},{g['y1']},{g['x2']},{g['y2']})")
                total_sent += 1
            else:
                try:
                    api.post_annotation(case_id, payload)
                    total_sent += 1
                except RuntimeError as e:
                    print(f"    [X] Gonderilemedi: {e}")
                    total_skipped += 1

    print(f"\nTamamlandi: {total_sent} annotation gonderildi, {total_skipped} atlatildi.")


if __name__ == "__main__":
    main()
