"""Tüm DICOM veri setini Abdomen dataset'ine toplu yükler ve annotasyon import eder.

İki aşama:
  Faz 1 — DICOM yükleme  : Egitim Verisi (T_) ve/veya Test Verisi (C_) altındaki tüm
           case dizinlerini zip'leyip POST /cases/upload'a gönderir.
           Zaten yüklenmiş case'ler atlanır (case_label'a göre).
  Faz 2 — Annotasyon import: manifest.csv'den bbox'ları okuyup z-sıralı
           webapp_image_id ile POST /cases/{id}/annotations'a yazar.
           Zaten annotasyonu olan case'ler atlanır.

Devam ettirilebilir: yarıda kalırsa tekrar çalıştırmak güvenlidir.

Kullanım:
  python webapp/scripts/bulk_import.py --email admin@ex.com --password pw
  python webapp/scripts/bulk_import.py --source train --email admin@ex.com --password pw
  python webapp/scripts/bulk_import.py --skip-upload --email admin@ex.com --password pw
  python webapp/scripts/bulk_import.py --dry-run
  python webapp/scripts/bulk_import.py --email a@b.com --password pw --dataset "Abdomen"
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import uuid
import warnings
import zipfile
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
# API istemcisi (stdlib-only, requests gerekmez)
# ---------------------------------------------------------------------------
import urllib.error
import urllib.parse
import urllib.request


class ApiClient:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self._token: str | None = None

    def _headers(self, content_type: str | None = "application/json") -> dict:
        h = {"Accept": "application/json"}
        if content_type:
            h["Content-Type"] = content_type
        if self._token:
            h["Authorization"] = f"Bearer {self._token}"
        return h

    def _json(self, method: str, path: str, data=None):
        url = f"{self.base}{path}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} {method} {path}: {e.read().decode()[:300]}") from e

    def login(self, email: str, password: str) -> None:
        form = urllib.parse.urlencode({"username": email, "password": password}).encode()
        req = urllib.request.Request(
            f"{self.base}/auth/login", data=form, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            self._token = json.loads(r.read())["access_token"]

    def get_datasets(self) -> list[dict]:
        return self._json("GET", "/datasets")

    def get_cases(self) -> list[dict]:
        return self._json("GET", "/cases")

    def upload_case(self, zip_bytes: bytes, case_label: str, dataset_id: str | None) -> dict:
        """Multipart/form-data ile DICOM zip yükler."""
        boundary = uuid.uuid4().hex
        body = io.BytesIO()

        def _field(name: str, value: str) -> None:
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
            body.write(f"{value}\r\n".encode())

        _field("case_label", case_label)
        if dataset_id:
            _field("dataset_id", dataset_id)

        # Dosya parçası
        body.write(f"--{boundary}\r\n".encode())
        body.write(f'Content-Disposition: form-data; name="file"; filename="{case_label}.zip"\r\n'.encode())
        body.write(b"Content-Type: application/zip\r\n\r\n")
        body.write(zip_bytes)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())

        raw = body.getvalue()
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(raw)),
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        req = urllib.request.Request(
            f"{self.base}/cases/upload",
            data=raw, method="POST", headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Upload hatası {case_label}: {e.read().decode()[:300]}") from e

    def get_case(self, case_id: str) -> dict:
        return self._json("GET", f"/cases/{case_id}")

    def post_annotation(self, case_id: str, payload: dict) -> dict:
        return self._json("POST", f"/cases/{case_id}/annotations", payload)

    def get_case_annotations(self, case_id: str) -> list[dict]:
        return self._json("GET", f"/cases/{case_id}/annotations")


# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def list_case_dirs(src_dir: Path) -> list[Path]:
    return sorted(
        (p for p in src_dir.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.name,
    )


def make_zip_bytes(case_dir: Path) -> bytes:
    dcm_files = sorted(
        (p for p in case_dir.glob("*.dcm") if not p.name.startswith("._")),
        key=lambda p: p.stem,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in dcm_files:
            zf.write(p, arcname=p.name)
    return buf.getvalue()


def find_case_by_label(cases: list[dict], case_key: str) -> dict | None:
    for c in cases:
        if case_key in (c.get("case_label") or ""):
            return c
    return None


def build_z_mapping(case_dir: Path) -> dict[int, int]:
    dcm_paths = [p for p in case_dir.glob("*.dcm") if not p.name.startswith("._")]
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


def parse_bboxes(bboxes_str) -> list[dict]:
    if not bboxes_str or (isinstance(bboxes_str, float) and str(bboxes_str) == "nan"):
        return []
    result = []
    for part in str(bboxes_str).split("|"):
        tokens = [t.strip() for t in part.split(",")]
        if len(tokens) != 5:
            continue
        try:
            cid, x1, y1, x2, y2 = map(int, tokens)
            result.append({"class_id": cid, "x1": x1, "y1": y1, "x2": x2, "y2": y2})
        except ValueError:
            continue
    return result


def wait_for_ready(api: ApiClient, case_id: str, label: str, timeout: int = 120) -> bool:
    """Case status 'ready' olana kadar bekler. Zaman aşımında False döner."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            c = api.get_case(case_id)
            if c["status"] == "ready":
                return True
            if c["status"] == "failed":
                print(f"    [!] {label}: ingest failed")
                return False
        except Exception:
            pass
        time.sleep(3)
    print(f"    [!] {label}: ready bekleme zaman aşımı ({timeout}s)")
    return False


# ---------------------------------------------------------------------------
# Faz 1 — DICOM yükleme
# ---------------------------------------------------------------------------
def phase_upload(
    api: ApiClient,
    sources: list[tuple[str, Path]],
    dataset_id: str | None,
    existing_labels: set[str],
    dry_run: bool,
) -> dict[str, str]:
    """Yüklenen case'lerin case_label → case_id eşleşmesini döner."""
    uploaded: dict[str, str] = {}
    total = sum(len(list_case_dirs(d)) for _, d in sources)
    done = 0

    for prefix, src_dir in sources:
        case_dirs = list_case_dirs(src_dir)
        print(f"\n[Faz1] {prefix}_ — {len(case_dirs)} case ({src_dir})")
        for case_dir in case_dirs:
            done += 1
            case_label = f"{prefix}_{case_dir.name}"
            prefix_str = f"[{done}/{total}] {case_label}"

            if case_label in existing_labels:
                print(f"  {prefix_str} — zaten yüklü, atlanıyor")
                continue

            dcm_count = sum(1 for _ in case_dir.glob("*.dcm") if not _.name.startswith("._"))
            if dcm_count == 0:
                print(f"  {prefix_str} — DICOM bulunamadı, atlanıyor")
                continue

            if dry_run:
                print(f"  {prefix_str} — [dry-run] {dcm_count} dilim yüklenecek")
                continue

            try:
                print(f"  {prefix_str} — zip oluşturuluyor ({dcm_count} dilim)...", end="", flush=True)
                zip_bytes = make_zip_bytes(case_dir)
                size_mb = len(zip_bytes) / (1024 * 1024)
                print(f" {size_mb:.1f} MB, yükleniyor...", end="", flush=True)
                result = api.upload_case(zip_bytes, case_label, dataset_id)
                case_id = result["id"]
                uploaded[case_label] = case_id
                print(f" OK (id={case_id[:8]})")
            except Exception as e:
                print(f" HATA: {e}")

    return uploaded


# ---------------------------------------------------------------------------
# Faz 2 — Annotasyon import
# ---------------------------------------------------------------------------
def phase_annotations(
    api: ApiClient,
    sources: list[tuple[str, Path]],
    manifest_df: pd.DataFrame,
    all_cases: list[dict],
    dry_run: bool,
    wait_ready: bool,
) -> None:
    total_sent = total_skipped = total_no_ann = 0

    for prefix, src_dir in sources:
        case_dirs = list_case_dirs(src_dir)
        print(f"\n[Faz2] {prefix}_ — {len(case_dirs)} case annotasyon import")

        for case_dir in case_dirs:
            case_label = f"{prefix}_{case_dir.name}"
            case_num = case_dir.name

            case_key = f"{prefix}_{case_num}"
            rows = manifest_df[
                (manifest_df["case"] == case_key) & (manifest_df["n_bbox_anns"] > 0)
            ]
            if rows.empty:
                total_no_ann += 1
                continue

            webapp_case = find_case_by_label(all_cases, case_label)
            if webapp_case is None:
                print(f"  [{case_label}] Webapp'te bulunamadı — önce upload yapın")
                total_skipped += len(rows)
                continue

            case_id = webapp_case["id"]

            # Zaten annotasyonu var mı?
            if not dry_run:
                try:
                    existing = api.get_case_annotations(case_id)
                    if existing:
                        print(f"  [{case_label}] {len(existing)} annotasyon zaten var, atlanıyor")
                        continue
                except Exception:
                    pass

            # Ready bekle
            if wait_ready and not dry_run:
                status = webapp_case.get("status", "")
                if status != "ready":
                    print(f"  [{case_label}] status={status}, ready bekleniyor...")
                    if not wait_for_ready(api, case_id, case_label):
                        total_skipped += len(rows)
                        continue
                    # Güncel case listesini yenile
                    all_cases[:] = api.get_cases()

            # Z-mapping
            try:
                z_map = build_z_mapping(case_dir)
            except Exception as e:
                print(f"  [{case_label}] Z-mapping hatası: {e}")
                total_skipped += 1
                continue

            # Annotasyonları yaz
            ann_count = 0
            for _, row in rows.iterrows():
                orig_id = int(row["image_id"])
                webapp_id = z_map.get(orig_id)
                if webapp_id is None:
                    continue
                for bbox in parse_bboxes(row["bboxes"]):
                    payload = {
                        "image_id": webapp_id,
                        "class_type": "lesion",
                        "class_id": bbox["class_id"],
                        "geometry_type": "bbox",
                        "geometry": {
                            "x1": bbox["x1"], "y1": bbox["y1"],
                            "x2": bbox["x2"], "y2": bbox["y2"],
                        },
                    }
                    if dry_run:
                        ann_count += 1
                        total_sent += 1
                    else:
                        try:
                            api.post_annotation(case_id, payload)
                            ann_count += 1
                            total_sent += 1
                        except Exception as e:
                            print(f"    [X] {e}")
                            total_skipped += 1

            print(f"  [{case_label}] {ann_count} annotasyon {'yazılacak [dry-run]' if dry_run else 'yazıldı'}")

    print(f"\n[Faz2] Tamamlandı: {total_sent} gönderildi, {total_skipped} atlandı, {total_no_ann} annotasyonsuz case")


# ---------------------------------------------------------------------------
# Ana mantık
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["train", "comp", "both"], default="train",
                        help="train=T_, comp=C_, both=ikisi (varsayılan)")
    parser.add_argument("--dataset", default="Abdomen",
                        help="Hedef dataset adı (varsayılan: Abdomen)")
    parser.add_argument("--api", default="http://localhost:8000/api/v1")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="Admin1234!")
    parser.add_argument("--manifest", type=Path, default=SPLIT_DIR / "manifest.csv")
    parser.add_argument("--skip-upload", action="store_true", help="Faz 1'i atla (sadece annotasyon import)")
    parser.add_argument("--skip-annotations", action="store_true", help="Faz 2'yi atla (sadece DICOM upload)")
    parser.add_argument("--no-wait", action="store_true", help="Ready bekleme (hızlı ama riskli)")
    parser.add_argument("--dry-run", action="store_true", help="API'ye yazmadan simüle et")
    args = parser.parse_args()

    # Kaynak dizinleri
    sources: list[tuple[str, Path]] = []
    if args.source in ("train", "both"):
        if EGITIM_DIR.exists():
            sources.append(("T", EGITIM_DIR))
        else:
            print(f"[!] Egitim dizini bulunamadı: {EGITIM_DIR}")
    if args.source in ("comp", "both"):
        if YARISMA_DIR.exists():
            sources.append(("C", YARISMA_DIR))
        else:
            print(f"[!] Test dizini bulunamadı: {YARISMA_DIR}")

    if not sources:
        raise SystemExit("Hiç kaynak dizin bulunamadı.")

    # Manifest
    if not args.skip_annotations:
        if not args.manifest.exists():
            raise SystemExit(f"manifest.csv bulunamadı: {args.manifest}\n"
                             "Sadece DICOM yükleme için --skip-annotations kullanın.")
        manifest_df = pd.read_csv(args.manifest)
        print(f"Manifest: {len(manifest_df)} satır")
    else:
        manifest_df = pd.DataFrame()

    # Auth
    api = ApiClient(args.api)
    if not args.dry_run:
        print(f"Giriş: {args.email} → {args.api}")
        try:
            api.login(args.email, args.password)
        except Exception as e:
            raise SystemExit(f"Auth hatası: {e}")

    # Dataset ID
    dataset_id: str | None = None
    if not args.dry_run:
        try:
            datasets = api.get_datasets()
            match = next((d for d in datasets if d["name"].lower() == args.dataset.lower()), None)
            if match:
                dataset_id = match["id"]
                print(f"Dataset '{args.dataset}' bulundu: {dataset_id}")
            else:
                names = [d["name"] for d in datasets]
                print(f"[!] '{args.dataset}' dataset bulunamadı. Mevcut: {names}")
                print("    Dataset olmadan devam ediliyor (dataset_id=None)")
        except Exception as e:
            print(f"[!] Dataset sorgusu hatası: {e}")

    # Mevcut case'ler
    all_cases: list[dict] = []
    existing_labels: set[str] = set()
    if not args.dry_run:
        print("Mevcut case'ler çekiliyor...")
        all_cases = api.get_cases()
        existing_labels = {c.get("case_label") or "" for c in all_cases}
        print(f"  {len(all_cases)} case zaten var")

    # ── Faz 1: DICOM upload ──
    if not args.skip_upload:
        uploaded = phase_upload(api, sources, dataset_id, existing_labels, args.dry_run)
        # Yeni yüklenen case'leri listeye ekle
        if uploaded and not args.dry_run:
            print(f"\n[Faz1] {len(uploaded)} yeni case yüklendi. Güncel case listesi alınıyor...")
            all_cases = api.get_cases()
    else:
        print("[Faz1] Atlandı (--skip-upload)")

    # ── Faz 2: Annotasyon import ──
    if not args.skip_annotations:
        if not args.dry_run and not all_cases:
            all_cases = api.get_cases()
        phase_annotations(
            api, sources, manifest_df, all_cases,
            dry_run=args.dry_run,
            wait_ready=not args.no_wait,
        )
    else:
        print("[Faz2] Atlandı (--skip-annotations)")

    print("\n✓ Tüm işlemler tamamlandı.")


if __name__ == "__main__":
    main()
