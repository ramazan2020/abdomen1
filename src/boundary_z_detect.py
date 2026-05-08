"""
TotalSegmentator tabanlı z-ekseni organ sınır tespiti.

YOLO'nun 2D görüntüde (x1, y1, x2, y2) bbox tespiti yapması gibi,
bu modül bir CT hacminde her organ için (z_start, z_end) kesit aralığını
tespit eder. Piksel maskesi yerine yalnızca kesit aralığı çıktısı alınır
— bu da doğrudan Bilgi.xlsx Boundary Slice annotasyonlarıyla eğitilebilir.

Akış
─────
Faz 1 — Sıfır-shot (eğitimsiz):
  CT → TotalSegmentator → organ mask → z-projeksiyon → z_start / z_end

Faz 2 — İnce ayar (Boundary Slice annotasyonlu):
  z-profil → 1D kalibrasyon modeli → daha hassas z_start / z_end

Sınıf eşlemesi  TS organ → bizim 6 anatomik sınıf
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import SimpleITK as sitk
except ImportError:
    sitk = None

from .config import ANATOMICAL_CLASSES, SEG_DATA_DIR, SPLIT_DIR, RAW_TRAIN_DIR, RAW_TEST_DIR
from .segmentation import _dicom_to_nifti, _m5_env


# ---------------------------------------------------------------------------
# TotalSegmentator çıktı organ adı → bizim anatomik sınıf (çok-organ birleştirme)
# ---------------------------------------------------------------------------
TS_ORGAN_MAP: Dict[str, str] = {
    # Abdominal Aorta
    "aorta":              "Abdominal Aorta",
    # Safra Kesesi
    "gallbladder":        "Gall bladder",
    # Pankreas
    "pancreas":           "Pancreas",
    # Böbrek + Mesane
    "kidney_left":        "Kidney-Bladder",
    "kidney_right":       "Kidney-Bladder",
    "urinary_bladder":    "Kidney-Bladder",
    # Kolon
    "colon":              "Colon",
    # Appendiks — TS'de ayrı sınıf değil, çekum bölgesinden alınır
    "cecum":              "appendix",   # TS v2+ 'cecum' sınıfı varsa kullan
    "appendix":           "appendix",   # TS v3+ ise doğrudan var
}

# Bizim 6 anatomik sınıf (Bilgi.xlsx ile aynı yazım)
OUR_ORGANS: List[str] = [
    "Abdominal Aorta",
    "Gall bladder",
    "Pancreas",
    "Kidney-Bladder",
    "Colon",
    "appendix",
]


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def _run_totalseg(input_nii: Path, out_dir: Path, fast: bool = True) -> None:
    """TotalSegmentator CLI çağrısı (fast mod öneriLir — sınır tespiti için yeterli)."""
    cmd = ["TotalSegmentator", "-i", str(input_nii), "-o", str(out_dir), "--task", "total"]
    if fast:
        cmd.append("--fast")
    subprocess.run(cmd, check=True, env=_m5_env())


def _z_profile(mask_nii_path: Path) -> np.ndarray:
    """
    Bir organ NIfTI maskesini okur; her z-kesitindeki pozitif voxel
    kesirini (fraction) döndürür. Şekil: (D,) — D = kesit sayısı.

    Kesit kesri = o kesitin kaçta kaçı organa ait.
    Sıfır kesit → organ yok, 1.0 → tüm kesit organ.
    """
    img = sitk.ReadImage(str(mask_nii_path))
    arr = sitk.GetArrayFromImage(img).astype(np.float32)  # (D, H, W) — z önce
    total_voxels = arr.shape[1] * arr.shape[2]
    return arr.sum(axis=(1, 2)) / max(total_voxels, 1)


def _detect_interval(
    z_profile: np.ndarray,
    threshold: float = 0.005,
    min_run: int = 2,
) -> Optional[Tuple[int, int]]:
    """
    z_profile üzerinde eşikleme yaparak organın bulunduğu en büyük
    ardışık z-aralığını döndürür.

    threshold : kesit kesri bu değerin üzerindeyse organ 'var' sayılır.
    min_run   : en az bu kadar ardışık kesit olmalı (gürültü filtresi).
    Döndürür  : (z_start, z_end) veya organ bulunamazsa None.
    """
    present = (z_profile > threshold).astype(np.int32)
    if present.sum() == 0:
        return None

    # Ardışık segmentleri bul, en uzununu al
    best_start, best_len = 0, 0
    cur_start, cur_len = 0, 0
    for z, p in enumerate(present):
        if p:
            if cur_len == 0:
                cur_start = z
            cur_len += 1
            if cur_len > best_len:
                best_len, best_start = cur_len, cur_start
        else:
            cur_len = 0

    if best_len < min_run:
        return None
    return best_start, best_start + best_len - 1


# ---------------------------------------------------------------------------
# Faz 1 — Sıfır-shot tahmin
# ---------------------------------------------------------------------------

def get_nifti_z_order(nii_path: Path) -> List[float]:
    """
    NIfTI dosyasındaki her z-kesitinin dünya koordinatındaki z-pozisyonunu döndürür.
    SimpleITK DICOM → NIfTI dönüşümünde z-ekseni orientation'a göre sıralanır.
    Döndürür: her z-indeks için z-koordinat (mm) listesi — uzunluğu = kesit sayısı.
    """
    img = sitk.ReadImage(str(nii_path))
    origin_z = img.GetOrigin()[2]
    spacing_z = img.GetSpacing()[2]
    n_slices  = img.GetSize()[2]
    return [origin_z + i * spacing_z for i in range(n_slices)]


def predict_boundaries_zero_shot(
    case_dir: Path,
    ts_cache_dir: Optional[Path] = None,
    nii_cache_dir: Optional[Path] = None,
    threshold: float = 0.005,
    min_run: int = 2,
) -> Dict[str, Optional[Tuple[int, int]]]:
    """
    Tek bir vaka için TotalSegmentator çalıştırır ve organ sınır
    kesitlerini döndürür.

    Döndürür:
        {organ_adı: (z_start, z_end)}
        z_start / z_end = NIfTI array'indeki z-indeksi (0-tabanlı).
        GT ile karşılaştırmak için build_gt_from_bilgi() aynı z-indeks
        uzayını kullanır (manifest image_id sıralaması).
    """
    if sitk is None:
        raise RuntimeError("SimpleITK kurulu değil: pip install SimpleITK")

    case_id = case_dir.name
    tmp_dir = Path("/tmp") / f"ts_bound_{case_id}"

    # --- NIfTI dönüşümü ---
    if nii_cache_dir is not None:
        nii_path = Path(nii_cache_dir) / f"{case_id}.nii.gz"
    else:
        nii_path = tmp_dir / "input.nii.gz"

    if not nii_path.exists():
        nii_path.parent.mkdir(parents=True, exist_ok=True)
        _dicom_to_nifti(case_dir, nii_path)

    # --- TotalSegmentator ---
    if ts_cache_dir is not None:
        ts_out = Path(ts_cache_dir) / case_id
    else:
        ts_out = tmp_dir / "ts"

    if not ts_out.exists() or not any(ts_out.glob("*.nii.gz")):
        ts_out.mkdir(parents=True, exist_ok=True)
        _run_totalseg(nii_path, ts_out, fast=True)

    # --- z-projeksiyon ve sınır tespiti ---
    # Önce her TS organ → bizim sınıf için profili birleştir
    organ_profiles: Dict[str, np.ndarray] = {}
    for ts_name, our_name in TS_ORGAN_MAP.items():
        mask_path = ts_out / f"{ts_name}.nii.gz"
        if not mask_path.exists():
            continue
        prof = _z_profile(mask_path)
        if our_name not in organ_profiles:
            organ_profiles[our_name] = prof
        else:
            organ_profiles[our_name] = np.maximum(organ_profiles[our_name], prof)

    results: Dict[str, Optional[Tuple[int, int]]] = {}
    for organ in OUR_ORGANS:
        if organ not in organ_profiles:
            results[organ] = None
        else:
            results[organ] = _detect_interval(
                organ_profiles[organ], threshold=threshold, min_run=min_run
            )

    return results


# ---------------------------------------------------------------------------
# Faz 2 — İnce ayar: 1D kalibrasyon modeli
# ---------------------------------------------------------------------------

class BoundaryCalibrator:
    """
    Her organ için bağımsız bir eşik (threshold) kalibre eder.
    Bilgi.xlsx Boundary Slice annotasyonlarını gözetimli sinyal olarak
    kullanır. Makine öğrenmesi yerine basit grid-search — küçük annotasyon
    seti için yeterlidir.

    Kullanım:
        cal = BoundaryCalibrator()
        cal.fit(z_profiles_train, boundary_gt_train)
        cal.save("calibrator.json")

        cal2 = BoundaryCalibrator.load("calibrator.json")
        preds = cal2.predict(z_profiles_test)
    """

    def __init__(self) -> None:
        # organ → en iyi threshold (varsayılan)
        self.thresholds: Dict[str, float] = {o: 0.005 for o in OUR_ORGANS}
        self.min_runs: Dict[str, int] = {o: 2 for o in OUR_ORGANS}

    def fit(
        self,
        profiles: Dict[str, List[np.ndarray]],      # organ → [z_profile_case1, ...]
        ground_truth: Dict[str, List[Optional[Tuple[int, int]]]],  # organ → [(z0,z1), ...]
        threshold_grid: Optional[List[float]] = None,
        min_run_grid: Optional[List[int]] = None,
    ) -> None:
        """
        Her organ için en iyi (threshold, min_run) ikilisini grid-search ile bulur.
        Metrik: ortalama z_start ve z_end MAE (kesit cinsinden).
        """
        if threshold_grid is None:
            threshold_grid = [0.001, 0.003, 0.005, 0.01, 0.02, 0.05]
        if min_run_grid is None:
            min_run_grid = [1, 2, 3, 5]

        for organ in OUR_ORGANS:
            profs = profiles.get(organ, [])
            gts = ground_truth.get(organ, [])
            if not profs or not any(g is not None for g in gts):
                continue

            best_mae = float("inf")
            best_thr, best_mr = 0.005, 2

            for thr in threshold_grid:
                for mr in min_run_grid:
                    maes = []
                    for prof, gt in zip(profs, gts):
                        if gt is None:
                            continue
                        pred = _detect_interval(prof, threshold=thr, min_run=mr)
                        if pred is None:
                            maes.append(50)          # ceza: organ bulunamadı
                        else:
                            maes.append(
                                (abs(pred[0] - gt[0]) + abs(pred[1] - gt[1])) / 2
                            )
                    mae = np.mean(maes)
                    if mae < best_mae:
                        best_mae, best_thr, best_mr = mae, thr, mr

            self.thresholds[organ] = best_thr
            self.min_runs[organ] = best_mr
            print(f"  {organ:<22} → thr={best_thr:.3f}, min_run={best_mr}, MAE={best_mae:.1f} kesit")

    def predict(
        self,
        profiles: Dict[str, np.ndarray],
    ) -> Dict[str, Optional[Tuple[int, int]]]:
        results = {}
        for organ in OUR_ORGANS:
            if organ not in profiles:
                results[organ] = None
            else:
                results[organ] = _detect_interval(
                    profiles[organ],
                    threshold=self.thresholds[organ],
                    min_run=self.min_runs[organ],
                )
        return results

    def save(self, path: str) -> None:
        import json
        with open(path, "w") as f:
            json.dump({"thresholds": self.thresholds, "min_runs": self.min_runs}, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "BoundaryCalibrator":
        import json
        obj = cls()
        with open(path) as f:
            data = json.load(f)
        obj.thresholds = data["thresholds"]
        obj.min_runs = data["min_runs"]
        return obj


# ---------------------------------------------------------------------------
# Toplu değerlendirme
# ---------------------------------------------------------------------------

def build_image_id_to_zidx(manifest_csv: Path) -> Dict[int, Dict[int, int]]:
    """
    manifest.csv'dan her vaka için:
        {case_id: {image_id: z_index}}
    eşlemesini döndürür.

    NIfTI dönüşümünde SimpleITK DICOM seriyi z-pozisyonuna göre sıralar.
    manifest'te image_id'ler de genellikle z-konumuyla monotonik ilişkilidir
    (CT acquisition order). Güvenli yaklaşım: image_id'ye göre sıralı rank.

    Not: Eğer DICOM'lar z-pozisyonuna göre farklı bir sırada ise
    dicom_utils.load_series() çıktısındaki sıra kullanılmalıdır.
    """
    manifest = pd.read_csv(manifest_csv)
    mapping: Dict[int, Dict[int, int]] = {}
    for case_id, grp in manifest.groupby("case"):
        # image_id'ye göre sırala → NIfTI z-eksenindeki sırayla eşleşir
        sorted_ids = grp["image_id"].sort_values().tolist()
        mapping[int(case_id)] = {int(img_id): z for z, img_id in enumerate(sorted_ids)}
    return mapping


def build_gt_from_bilgi(
    bilgi_xlsx: Path,
    manifest_csv: Path,
    split_csv: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Bilgi.xlsx'tan Boundary Slice annotasyonlarını okuyarak
    (case, organ, img_id_start, img_id_end, z_start, z_end) formatında
    bir DataFrame döndürür.

    Image Id (DICOM instance numarası) → z-index dönüşümü manifest_csv
    üzerinden yapılır: her case'in kesitleri image_id'ye göre sıralanır,
    bu sıradaki konum z-index olur.

    Örnek (case 20001, Abdominal Aorta):
        Boundary Slice Image Id'leri: 100017, 100047
        Manifest'te case 20001'in kesit sırası: 100007(0), 100008(1), ..., 100017(k), ...
        → z_start = k, z_end = m
    """
    xl = pd.read_excel(bilgi_xlsx)
    bs = xl[xl["Type"].str.strip().str.lower() == "boundary slice"].copy()

    # Image Id → z-index eşlemesi
    id_to_z = build_image_id_to_zidx(manifest_csv)

    skipped = 0
    rows = []
    for (case, organ), grp in bs.groupby(["Case Number", "Class"]):
        case = int(case)
        image_ids = grp["Image Id"].dropna().astype(int).tolist()
        if len(image_ids) < 2:
            # Yalnızca tek boundary varsa atla (annotasyon eksik)
            skipped += 1
            continue

        case_map = id_to_z.get(case, {})
        if not case_map:
            skipped += 1
            continue

        # Image Id'leri z-index'e çevir
        z_indices = []
        for img_id in image_ids:
            z = case_map.get(img_id)
            if z is not None:
                z_indices.append(z)

        if len(z_indices) < 2:
            skipped += 1
            continue

        rows.append({
            "case":         case,
            "organ":        organ.strip(),
            "img_id_start": min(image_ids),
            "img_id_end":   max(image_ids),
            "z_start":      min(z_indices),   # NIfTI z-eksenindeki indeks
            "z_end":        max(z_indices),
        })

    df = pd.DataFrame(rows)
    if skipped:
        print(f"  [build_gt] {skipped} organ-vaka atlandı (tek boundary veya manifest'te yok)")

    if split_csv is not None:
        valid = set(pd.read_csv(split_csv)["Case Number"])
        df = df[df["case"].isin(valid)]
    return df


def evaluate(
    pred_rows: List[Dict],
    gt_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    pred_rows : [{"case": id, "organ": name, "z_start": int, "z_end": int}, ...]
    gt_df     : build_gt_from_bilgi() çıktısı

    Döndürür  : organ bazlı MAE ve tespit oranı.
    """
    pred_df = pd.DataFrame(pred_rows)
    merged = pd.merge(
        pred_df, gt_df,
        on=["case", "organ"], suffixes=("_pred", "_gt"),
    )

    results = []
    for organ, grp in merged.groupby("organ"):
        mae_start = (grp["z_start_pred"] - grp["z_start_gt"]).abs().mean()
        mae_end   = (grp["z_end_pred"]   - grp["z_end_gt"]).abs().mean()
        mae_len   = (
            (grp["z_end_pred"] - grp["z_start_pred"]) -
            (grp["z_end_gt"]   - grp["z_start_gt"])
        ).abs().mean()
        results.append({
            "organ": organ,
            "n": len(grp),
            "mae_z_start": round(mae_start, 1),
            "mae_z_end":   round(mae_end,   1),
            "mae_length":  round(mae_len,    1),
        })
    return pd.DataFrame(results).sort_values("mae_z_start")


# ---------------------------------------------------------------------------
# Toplu pipeline — tüm vakalar
# ---------------------------------------------------------------------------

def run_dataset(
    case_dirs: List[Path],
    ts_cache_dir: Path,
    nii_cache_dir: Path,
    calibrator: Optional[BoundaryCalibrator] = None,
    threshold: float = 0.005,
) -> pd.DataFrame:
    """
    Bir vaka listesi üzerinde Faz-1 (veya kalibreli Faz-2) tahminini çalıştırır.
    Döndürür: (case, organ, z_start, z_end) DataFrame.
    """
    rows = []
    for case_dir in tqdm(case_dirs, desc="Boundary Z-Detect"):
        try:
            raw_preds = predict_boundaries_zero_shot(
                case_dir,
                ts_cache_dir=ts_cache_dir,
                nii_cache_dir=nii_cache_dir,
                threshold=threshold,
            )
            if calibrator is not None:
                # Önce z-profillerini yeniden hesapla (kalibre için)
                ts_out = ts_cache_dir / case_dir.name
                organ_profiles: Dict[str, np.ndarray] = {}
                for ts_name, our_name in TS_ORGAN_MAP.items():
                    mask_path = ts_out / f"{ts_name}.nii.gz"
                    if not mask_path.exists():
                        continue
                    prof = _z_profile(mask_path)
                    if our_name not in organ_profiles:
                        organ_profiles[our_name] = prof
                    else:
                        organ_profiles[our_name] = np.maximum(organ_profiles[our_name], prof)
                preds = calibrator.predict(organ_profiles)
            else:
                preds = raw_preds

            for organ, interval in preds.items():
                if interval is not None:
                    rows.append({
                        "case": int(case_dir.name),
                        "organ": organ,
                        "z_start": interval[0],
                        "z_end": interval[1],
                    })
        except Exception as exc:
            print(f"[skip] case {case_dir.name}: {exc}")

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Organ z-sınır tespiti (TotalSegmentator tabanlı)")
    sub = ap.add_subparsers(dest="cmd")

    # -- predict
    p_pred = sub.add_parser("predict", help="Tek vaka tahmin")
    p_pred.add_argument("case_dir", type=Path)
    p_pred.add_argument("--calibrator", type=Path, default=None)
    p_pred.add_argument("--threshold", type=float, default=0.005)

    # -- dataset
    p_ds = sub.add_parser("dataset", help="Toplu tahmin (tüm vakalar)")
    p_ds.add_argument("--split-csv", type=Path, default=None)
    p_ds.add_argument("--out-csv", type=Path, default=Path("boundary_preds.csv"))
    p_ds.add_argument("--calibrator", type=Path, default=None)

    # -- calibrate
    p_cal = sub.add_parser("calibrate", help="Bilgi.xlsx ile kalibrasyon")
    p_cal.add_argument("bilgi_xlsx", type=Path)
    p_cal.add_argument("--manifest-csv", type=Path, default=None)
    p_cal.add_argument("--split-csv", type=Path, default=None)
    p_cal.add_argument("--out-calibrator", type=Path, default=Path("boundary_calibrator.json"))

    # -- evaluate
    p_ev = sub.add_parser("evaluate", help="Tahminleri GT ile karşılaştır")
    p_ev.add_argument("pred_csv", type=Path)
    p_ev.add_argument("bilgi_xlsx", type=Path)
    p_ev.add_argument("--manifest-csv", type=Path, default=None)
    p_ev.add_argument("--split-csv", type=Path, default=None)

    args = ap.parse_args()

    TS_CACHE  = SEG_DATA_DIR / "ts_cache"
    NII_CACHE = SEG_DATA_DIR / "nii_cache"
    TS_CACHE.mkdir(parents=True, exist_ok=True)
    NII_CACHE.mkdir(parents=True, exist_ok=True)

    if args.cmd == "predict":
        cal = BoundaryCalibrator.load(str(args.calibrator)) if args.calibrator else None
        preds = predict_boundaries_zero_shot(
            args.case_dir, ts_cache_dir=TS_CACHE, nii_cache_dir=NII_CACHE,
            threshold=args.threshold,
        )
        print(f"\nVaka: {args.case_dir.name}")
        print(f"{'Organ':<25} {'z_start':>8} {'z_end':>8} {'uzunluk':>8}")
        print("-" * 55)
        for organ, iv in preds.items():
            if iv:
                print(f"{organ:<25} {iv[0]:>8} {iv[1]:>8} {iv[1]-iv[0]+1:>8}")
            else:
                print(f"{organ:<25} {'—':>8} {'—':>8} {'—':>8}")

    elif args.cmd == "dataset":
        cal = BoundaryCalibrator.load(str(args.calibrator)) if args.calibrator else None
        all_dirs: List[Path] = []
        for src in (RAW_TRAIN_DIR, RAW_TEST_DIR):
            if src.exists():
                all_dirs.extend(sorted(p for p in src.iterdir() if p.is_dir()))
        if args.split_csv and args.split_csv.exists():
            valid = set(pd.read_csv(args.split_csv)["Case Number"].astype(int))
            all_dirs = [d for d in all_dirs if int(d.name) in valid]
        df = run_dataset(all_dirs, TS_CACHE, NII_CACHE, calibrator=cal)
        df.to_csv(args.out_csv, index=False)
        print(f"\nSonuçlar kaydedildi: {args.out_csv} ({len(df)} satır)")

    elif args.cmd == "calibrate":
        manifest_csv = args.manifest_csv or (SPLIT_DIR / "manifest.csv")
        gt = build_gt_from_bilgi(args.bilgi_xlsx, manifest_csv, args.split_csv)
        print(f"GT annotasyon: {len(gt)} satır")
        print("NOT: Kalibrasyon için önce 'dataset' komutuyla TS çıktılarını üretin.")

    elif args.cmd == "evaluate":
        manifest_csv = args.manifest_csv or (SPLIT_DIR / "manifest.csv")
        pred_df = pd.read_csv(args.pred_csv)
        gt_df = build_gt_from_bilgi(args.bilgi_xlsx, manifest_csv, args.split_csv)
        pred_rows = pred_df.to_dict("records")
        result = evaluate(pred_rows, gt_df)
        print("\nDeğerlendirme Sonuçları (MAE: kesit cinsinden)")
        print(result.to_string(index=False))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
