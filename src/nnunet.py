"""
nnU-Net v2 için tam pipeline: NIfTI dönüşüm → dataset hazırlık → eğitim → tahmin.

Ana sınıf: NnUNetPipeline

Bu sınıf; preprocess notebook'undaki ve train notebook'undaki tüm nnUNet mantığını
tek bir yeniden kullanılabilir nesneye toplar. Notebook'lar yalnızca bu sınıfı çağırır.

Örnek kullanım:
    from src.nnunet import NnUNetPipeline
    from src.splits import load_fold
    import pandas as pd

    pipe = NnUNetPipeline(fold=0, nifti_dir=NIFTI_DIR, nnunet_root=NND_ROOT)
    manifest = pd.read_csv(SPLIT_DIR / "manifest.csv")

    train_cases = load_fold(0, "train")
    val_cases   = load_fold(0, "val")

    pipe.convert_to_nifti(train_cases + val_cases, source_dir=EGITIM_DIR)
    pipe.build_dataset(train_cases, val_cases, manifest, source_dir=EGITIM_DIR)
    pipe.plan_and_preprocess()
    pipe.train()

    pred_dir = pipe.predict(pipe.val_input_dir, pipe.val_output_dir)
    pred_df  = pipe.seg_to_bboxes(pred_dir)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sysconfig
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    import SimpleITK as sitk
except Exception:                       # pragma: no cover
    sitk = None

try:
    from scipy import ndimage as _ndimage
except Exception:                       # pragma: no cover
    _ndimage = None

from .config import SUPER_CLASSES
from .dicom_utils import DicomVolume
from .lifting import BboxLifter
from .splits import raw_case_id


# ---------------------------------------------------------------------------
# YARDIMCI FONKSİYONLAR
# ---------------------------------------------------------------------------
def _find_cmd(name: str) -> str:
    """nnUNet komutunu PATH ve sysconfig script dizinlerinde arar."""
    p = shutil.which(name)
    if p:
        return p
    for d in [
        sysconfig.get_path("scripts"),
        str(Path(__import__("sys").executable).parent),
        "/usr/local/bin",
        "/opt/conda/bin",
    ]:
        c = Path(d) / name
        if c.exists():
            return str(c)
    return name  # fallback: PATH üzerinde olduğunu umuyoruz


# ---------------------------------------------------------------------------
# PIPELINE
# ---------------------------------------------------------------------------
class NnUNetPipeline:
    """
    nnU-Net v2 iş akışının tamamını kapsayan pipeline sınıfı.

    Parametreler:
        fold        : Kullanılan fold numarası (0-indexed).
        nifti_dir   : DICOM → NIfTI dönüştürülmüş dosyaların saklanacağı dizin.
        nnunet_root : nnunet_raw / nnunet_preprocessed / nnunet_results
                      için kök dizin.
        dataset_id  : nnU-Net dataset ID (varsayılan 100).
        dataset_name: nnU-Net dataset ismi (varsayılan "Abdomen").
    """

    def __init__(
        self,
        fold: int,
        nifti_dir: Path,
        nnunet_root: Path,
        dataset_id: int = 100,
        dataset_name: str = "Abdomen",
    ) -> None:
        self.fold = fold
        self.nifti_dir = Path(nifti_dir)
        self.nnunet_root = Path(nnunet_root)
        self.dataset_id = dataset_id
        self.dataset_name = dataset_name

        # Standart nnU-Net dizin yapısı
        self.raw_dir          = self.nnunet_root / "nnunet_raw"
        self.preprocessed_dir = self.nnunet_root / "nnunet_preprocessed"
        self.results_dir      = self.nnunet_root / "nnunet_results"
        self.dataset_dir      = self.raw_dir / f"Dataset{dataset_id}_{dataset_name}"
        self.images_tr        = self.dataset_dir / "imagesTr"
        self.labels_tr        = self.dataset_dir / "labelsTr"

        # Tahmin giriş/çıkış dizinleri (nnunet_raw dışında)
        self.val_input_dir  = self.nnunet_root / "val_input_raw"
        self.val_output_dir = (
            self.results_dir
            / f"Dataset{dataset_id}_{dataset_name}"
            / "nnUNetTrainer__nnUNetPlans__3d_fullres"
            / f"fold_{fold}"
            / "val_predictions"
        )

        self._setup_env()

    # ------------------------------------------------------------------
    # Kurulum
    # ------------------------------------------------------------------
    def _setup_env(self) -> None:
        """nnU-Net ortam değişkenlerini ayarlar; gerekli dizinleri oluşturur."""
        os.environ["nnUNet_raw"]          = str(self.raw_dir)
        os.environ["nnUNet_preprocessed"] = str(self.preprocessed_dir)
        os.environ["nnUNet_results"]      = str(self.results_dir)
        os.environ.setdefault("OMP_NUM_THREADS", "1")

        for d in [
            self.raw_dir, self.preprocessed_dir, self.results_dir,
            self.images_tr, self.labels_tr,
            self.nifti_dir, self.val_input_dir, self.val_output_dir,
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def use_local_preprocessed(self, local_dir: Path) -> None:
        """
        Colab'da Drive yerine yerel diske kopyalanmış preprocessed dizinini kullan.
        Kopyalama işleminden SONRA bu metot çağrılmalıdır.
        """
        self.preprocessed_dir = Path(local_dir)
        os.environ["nnUNet_preprocessed"] = str(self.preprocessed_dir)

    # ------------------------------------------------------------------
    # 1. DICOM → NIfTI
    # ------------------------------------------------------------------
    def convert_to_nifti(
        self,
        cases: List[str],
        source_dir: Path,
        n_workers: int = 4,
    ) -> Dict[str, str]:
        """
        Verilen vaka listesini NIfTI'ye dönüştürür (paralel, eksikleri atlar).

        Dönüş: {case_id: "ok" | "skip" | "no_dcm" | "err:<mesaj>"}
        """
        source_dir = Path(source_dir)

        def _convert(case: str) -> Tuple[str, str]:
            raw = raw_case_id(case)
            out = self.nifti_dir / f"case_{raw:05d}_0000.nii.gz"
            try:
                status = "skip" if out.exists() else "ok"
                if not out.exists():
                    DicomVolume(source_dir / str(raw)).to_nifti(out)
                return case, status
            except RuntimeError as e:
                if "bulunamadı" in str(e) or "not found" in str(e).lower():
                    return case, "no_dcm"
                return case, f"err:{e}"
            except Exception as e:
                return case, f"err:{e}"

        results: Dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=n_workers) as ex:
            for case, status in tqdm(
                ex.map(_convert, cases), total=len(cases), desc="DICOM→NIfTI"
            ):
                results[case] = status

        ok   = sum(1 for s in results.values() if s == "ok")
        skip = sum(1 for s in results.values() if s == "skip")
        errs = {c: s for c, s in results.items() if s not in ("ok", "skip")}
        print(f"NIfTI: {ok} yeni, {skip} atlandı, {len(errs)} hata")
        if errs:
            for c, s in list(errs.items())[:5]:
                print(f"  {c}: {s}")
        return results

    # ------------------------------------------------------------------
    # 2. Dataset hazırlık (imagesTr / labelsTr)
    # ------------------------------------------------------------------
    def build_dataset(
        self,
        train_cases: List[str],
        val_cases: List[str],
        manifest: pd.DataFrame,
        source_dir: Path,
        delta_z: int = 2,
        iou_th: float = 0.3,
    ) -> Path:
        """
        imagesTr / labelsTr dizinlerini doldurur ve splits_final.json yazar.

        - Her vaka için NIfTI sembolik linki (veya kopyası) imagesTr'ye eklenir.
        - BboxLifter ile semantic maske üretilir ve labelsTr'ye yazılır.
        - nnU-Net'in otomatik split'i geçersiz kılınmak için splits_final.json yazılır.
        """
        if sitk is None:
            raise RuntimeError("SimpleITK kurulu değil; `pip install SimpleITK`")

        source_dir = Path(source_dir)
        lifter = BboxLifter(manifest, egitim_dir=source_dir,
                            delta_z=delta_z, iou_th=iou_th)
        all_cases = list(dict.fromkeys(train_cases + val_cases))

        # dataset.json
        self._write_dataset_json(len(all_cases))

        ok = skip = miss = 0
        for case in tqdm(all_cases, desc="build_dataset"):
            raw = raw_case_id(case)
            src_nii = self.nifti_dir / f"case_{raw:05d}_0000.nii.gz"
            if not src_nii.exists():
                miss += 1
                continue

            # imagesTr linki / kopyası
            dst_img = self.images_tr / f"case_{raw:05d}_0000.nii.gz"
            self._link_or_copy(src_nii, dst_img)

            # labelsTr semantic maske
            dst_lbl = self.labels_tr / f"case_{raw:05d}.nii.gz"
            if dst_lbl.exists():
                skip += 1
                continue

            img_itk  = sitk.ReadImage(str(src_nii))
            img_arr  = sitk.GetArrayFromImage(img_itk)
            mask_arr = lifter.build_semantic_mask(case, img_arr.shape)
            mask_itk = sitk.GetImageFromArray(mask_arr)
            mask_itk.CopyInformation(img_itk)
            sitk.WriteImage(mask_itk, str(dst_lbl))
            ok += 1

        print(f"Dataset: {ok} yeni, {skip} atlandı, {miss} NIfTI eksik")

        # splits_final.json
        self._write_splits_json(train_cases, val_cases)

        n_img = len(list(self.images_tr.glob("*.nii.gz")))
        n_lbl = len(list(self.labels_tr.glob("*.nii.gz")))
        print(f"imagesTr={n_img}, labelsTr={n_lbl}")
        return self.dataset_dir

    # ------------------------------------------------------------------
    # 3. Plan + Preprocess
    # ------------------------------------------------------------------
    def plan_and_preprocess(self, timeout: int = 3600) -> None:
        """nnUNetv2_plan_and_preprocess çalıştırır."""
        cmd = _find_cmd("nnUNetv2_plan_and_preprocess")
        print(f"Plan+Preprocess: {cmd}")
        r = subprocess.run(
            [cmd, "-d", str(self.dataset_id), "-c", "3d_fullres",
             "--verify_dataset_integrity"],
            env={**os.environ}, capture_output=True, text=True, timeout=timeout,
        )
        if r.returncode != 0:
            print("STDERR:\n", r.stderr[-2000:])
            raise RuntimeError("plan_and_preprocess başarısız")
        print("plan_and_preprocess tamamlandı.")

    # ------------------------------------------------------------------
    # 4. Eğitim
    # ------------------------------------------------------------------
    def train(self, npz: bool = True, timeout: int = 36000) -> Path:
        """
        nnUNetv2_train çalıştırır.
        Dönüş: en iyi checkpoint dizini.
        """
        cmd = _find_cmd("nnUNetv2_train")
        args = [cmd, str(self.dataset_id), "3d_fullres", str(self.fold)]
        if npz:
            args.append("--npz")
        print(f"Eğitim başlatılıyor: {' '.join(args)}")
        r = subprocess.run(
            args, env={**os.environ},
            capture_output=True, text=True, timeout=timeout,
        )
        print("--- stdout ---\n", r.stdout[-3000:])
        if r.returncode != 0:
            print("--- stderr ---\n", r.stderr[-1000:])
            raise RuntimeError(f"nnUNetv2_train hata kodu: {r.returncode}")
        checkpoint_dir = (
            self.results_dir
            / f"Dataset{self.dataset_id}_{self.dataset_name}"
            / "nnUNetTrainer__nnUNetPlans__3d_fullres"
            / f"fold_{self.fold}"
        )
        return checkpoint_dir

    # ------------------------------------------------------------------
    # 5. Tahmin
    # ------------------------------------------------------------------
    def predict(
        self,
        input_dir: Path,
        output_dir: Path,
        save_probabilities: bool = True,
        timeout: int = 36000,
    ) -> Path:
        """
        nnUNetv2_predict çalıştırır.
        Dönüş: tahmin maskeleri dizini.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        cmd = _find_cmd("nnUNetv2_predict")
        args = [
            cmd,
            "-i", str(input_dir),
            "-o", str(output_dir),
            "-d", str(self.dataset_id),
            "-c", "3d_fullres",
            "-f", str(self.fold),
        ]
        if save_probabilities:
            args.append("--save_probabilities")
        r = subprocess.run(
            args, env={**os.environ},
            capture_output=True, text=True, timeout=timeout,
        )
        print("STDOUT:\n", r.stdout[-2000:])
        if r.returncode != 0:
            print("STDERR:\n", r.stderr[-1000:])
            raise RuntimeError(f"nnUNetv2_predict hata kodu: {r.returncode}")
        preds = list(output_dir.glob("*.nii.gz"))
        print(f"Tahmin tamamlandı: {len(preds)} NIfTI mask")
        return output_dir

    def link_val_inputs(self) -> int:
        """
        Val görüntülerini val_input_dir'a sembolik link olarak ekler.
        Dönüş: eklenen dosya sayısı.
        """
        linked = 0
        for src in self.images_tr.glob("*.nii.gz"):
            dst = self.val_input_dir / src.name
            if not dst.exists():
                try:
                    os.symlink(src, dst)
                except (OSError, NotImplementedError):
                    shutil.copy2(src, dst)
                linked += 1
        print(f"val_input_dir: {len(list(self.val_input_dir.glob('*.nii.gz')))} dosya "
              f"({linked} yeni)")
        return linked

    # ------------------------------------------------------------------
    # 6. Maske → bbox projeksiyon
    # ------------------------------------------------------------------
    def seg_to_bboxes(self, pred_dir: Path) -> pd.DataFrame:
        """
        nnU-Net tahmin dizinindeki NIfTI maskelerini 2D bounding box
        DataFrame'ine dönüştürür.

        Her bağlı bileşen (connected component) ayrı bir lezyon örneği olarak
        işlenir ve kapsadığı her z-kesitine yansıtılır.

        Güven skoru:
        - .npz olasılık dosyası varsa: ilgili sınıfın ortalama softmax değeri
        - yoksa: bileşenin voksel sayısı / toplam sınıf vokseli

        Dönüş sütunları: case, image_id, class, score, x1, y1, x2, y2
        """
        if _ndimage is None:
            raise RuntimeError("scipy kurulu değil; `pip install scipy`")
        if sitk is None:
            raise RuntimeError("SimpleITK kurulu değil; `pip install SimpleITK`")

        all_rows: List[dict] = []
        for nii_path in sorted(Path(pred_dir).glob("*.nii.gz")):
            all_rows.extend(self._process_pred_nii(nii_path))

        df = pd.DataFrame(all_rows)
        print(f"seg_to_bboxes: {len(df):,} satır, "
              f"{df['case'].nunique() if not df.empty else 0} vaka")
        return df

    def _process_pred_nii(self, path: Path) -> List[dict]:
        """Tek NIfTI tahmin dosyasını 2D bbox satırlarına dönüştürür."""
        # case_20001_0000.nii.gz veya case_20001.nii.gz → raw int 20001
        stem_parts = path.stem.replace(".nii", "").split("_")
        try:
            case_raw = int(stem_parts[1])
        except (IndexError, ValueError):
            return []

        mask = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))  # [Z, Y, X]

        prob_path = path.with_suffix("").with_suffix(".npz")
        probs = None
        if prob_path.exists():
            probs = np.load(prob_path)["probabilities"]  # [C, Z, Y, X]

        rows: List[dict] = []
        for label_id in range(1, len(SUPER_CLASSES) + 1):
            binary = (mask == label_id).astype(np.uint8)
            if binary.sum() == 0:
                continue
            labeled, n_comp = _ndimage.label(binary)
            total_vox = float(binary.sum())

            for comp_id in range(1, n_comp + 1):
                comp_mask = labeled == comp_id
                coords = np.where(comp_mask)
                z1, z2 = int(coords[0].min()), int(coords[0].max())
                y1, y2 = int(coords[1].min()), int(coords[1].max())
                x1, x2 = int(coords[2].min()), int(coords[2].max())

                score = (
                    float(probs[label_id][comp_mask].mean())
                    if probs is not None
                    else float(comp_mask.sum()) / total_vox
                )

                for z in range(z1, z2 + 1):
                    rows.append({
                        "case": case_raw,
                        "image_id": z,
                        "class": label_id - 1,
                        "score": score,
                        "x1": float(x1), "y1": float(y1),
                        "x2": float(x2), "y2": float(y2),
                    })
        return rows

    # ------------------------------------------------------------------
    # Dahili yardımcılar
    # ------------------------------------------------------------------
    def _write_dataset_json(self, n_training: int) -> None:
        path = self.dataset_dir / "dataset.json"
        if path.exists():
            return
        meta = {
            "channel_names": {"0": "CT"},
            "labels": {
                "background": 0,
                **{name: i + 1 for i, name in enumerate(SUPER_CLASSES)},
            },
            "numTraining": n_training,
            "file_ending": ".nii.gz",
        }
        path.write_text(json.dumps(meta, indent=2))
        print(f"dataset.json yazıldı: {path}")

    def _write_splits_json(
        self, train_cases: List[str], val_cases: List[str]
    ) -> None:
        splits_dir = self.preprocessed_dir / f"Dataset{self.dataset_id}_{self.dataset_name}"
        splits_dir.mkdir(parents=True, exist_ok=True)
        path = splits_dir / "splits_final.json"
        splits = [{
            "train": [f"case_{raw_case_id(c):05d}" for c in train_cases],
            "val":   [f"case_{raw_case_id(c):05d}" for c in val_cases],
        }]
        path.write_text(json.dumps(splits, indent=2))
        print(f"splits_final.json yazıldı ({len(train_cases)} train / {len(val_cases)} val)")

    @staticmethod
    def _link_or_copy(src: Path, dst: Path) -> None:
        if dst.exists():
            return
        try:
            os.symlink(src, dst)
        except (OSError, NotImplementedError):
            shutil.copy2(src, dst)
