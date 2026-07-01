"""Mimari-bazlı inference sarmalayıcıları (plan Bölüm 4 tablosu).

Faz 2: yolo_det — src.detection.predict_volume doğrudan kullanılabilir.
Faz 5: yolo_seg, nnunet, cls_timm, organ_bag_transformer eklendi.
RF-DETR / D-FINE / MedNeXt: src/ kodu olmadığından MLDependencyUnavailable
  fırlatmaya devam eder, job 'failed' olur, sunucu/worker çökmez.
"""
from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Annotation, AnnotationGroup, Case, ClassificationPrediction,
    InferenceBatch, InferenceRun, ModelOutput, ModelVersion,
)
from app.db.session import SessionLocal
from app.services.storage_service import get_storage_backend
from app.services.job_queue import get_queue

logger = logging.getLogger(__name__)


class MLDependencyUnavailable(RuntimeError):
    """Mimari için gerekli ML kütüphanesi (torch/ultralytics/nnunet) kurulu
    değil veya henüz sarmalayıcı yazılmadı. Job bunu yakalayıp 'failed' yapar —
    backend/worker süreci çökmez."""


@dataclass
class ArchitectureOutput:
    """Her mimari handler'ın ortak dönüş tipi.

    bbox_rows : [{"image_id": int, "class": int, "x1": f, "y1": f, "x2": f, "y2": f, "score": f}]
    cls_rows  : [{"image_id": int|None, "class_id": int, "probability": float}]
                 image_id=None → vaka-seviyesi tahmin
    """
    bbox_rows: list[dict] = field(default_factory=list)
    cls_rows: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Mimari handler'ları
# ---------------------------------------------------------------------------

def _predict_yolo_det(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    try:
        from src.detection import predict_volume
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "ultralytics/torch bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    weights_path = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)
    df = predict_volume(weights=weights_path, case_dir=case_dir, conf=conf_threshold, min_slice_run=min_slice_run)
    rows = df.to_dict("records") if df is not None and len(df) else []
    return ArchitectureOutput(bbox_rows=rows, cls_rows=[])


def _predict_yolo_seg(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    """YOLO-seg: her DICOM dilimi için bbox çıkarır (segmentasyon maskesinden)."""
    try:
        import numpy as np
        from ultralytics import YOLO
        from src.dicom_utils import load_series, hu_to_three_channel
        from src.config import DEFAULT_WINDOWS
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "ultralytics/torch bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    weights_path = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)

    model = YOLO(str(weights_path))
    series = load_series(case_dir)  # CTSeries: .hu (Z,Y,X), .image_ids

    bbox_rows: list[dict] = []
    for z, image_id in enumerate(series.image_ids):
        hu_slice = series.hu[z]  # (Y, X)
        img = (hu_to_three_channel(hu_slice, DEFAULT_WINDOWS) * 255).astype(np.uint8)
        results = model.predict(img, conf=conf_threshold, verbose=False)
        if not results or results[0].boxes is None:
            continue
        boxes = results[0].boxes
        xyxy = boxes.xyxy.cpu().numpy()
        cls = boxes.cls.cpu().numpy()
        conf = boxes.conf.cpu().numpy()
        for b, c, sc in zip(xyxy, cls, conf):
            bbox_rows.append({
                "image_id": image_id,
                "class": int(c),
                "x1": float(b[0]), "y1": float(b[1]),
                "x2": float(b[2]), "y2": float(b[3]),
                "score": float(sc),
            })

    return ArchitectureOutput(bbox_rows=bbox_rows, cls_rows=[])


def _predict_nnunet(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    """nnU-Net: DICOM → NIfTI → nnUNetv2_predict (subprocess) → seg_to_bboxes."""
    try:
        from src.nnunet import NnUNetPipeline
        from src.dicom_utils import DicomVolume
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "nnunet/SimpleITK bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    nnunet_root = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)

    with tempfile.TemporaryDirectory(prefix="webapp_nnunet_") as tmpdir:
        tmpdir = Path(tmpdir)
        nifti_dir = tmpdir / "nifti"
        input_dir = tmpdir / "input"
        output_dir = tmpdir / "output"
        nifti_dir.mkdir()
        input_dir.mkdir()
        output_dir.mkdir()

        nifti_path = nifti_dir / "case_00001_0000.nii.gz"
        DicomVolume(case_dir).to_nifti(nifti_path)

        # nnUNet beklenen input dosya ismi
        import shutil
        shutil.copy2(nifti_path, input_dir / "case_00001_0000.nii.gz")

        pipeline = NnUNetPipeline(fold=0, nifti_dir=nifti_dir, nnunet_root=nnunet_root)
        pipeline.predict(input_dir, output_dir)
        df = pipeline.seg_to_bboxes(output_dir)

    if df is None or len(df) == 0:
        return ArchitectureOutput(bbox_rows=[], cls_rows=[])

    bbox_rows: list[dict] = [
        {
            "image_id": int(row["image_id"]),
            "class": int(row["class"]),
            "x1": float(row["x1"]),
            "y1": float(row["y1"]),
            "x2": float(row["x2"]),
            "y2": float(row["y2"]),
            "score": float(row.get("score", 1.0)),
        }
        for _, row in df.iterrows()
    ]
    return ArchitectureOutput(bbox_rows=bbox_rows, cls_rows=[])


def _predict_cls_timm(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    """cls_timm: dilim-düzeyi + vaka-düzeyi çok-etiket sınıflandırma."""
    try:
        import numpy as np
        import torch
        import torch.nn.functional as F
        from src.train_cls import build_model
        from src.config import DEFAULT_CLS, DEFAULT_WINDOWS
        from src.dicom_utils import load_series, hu_to_three_channel
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "timm/torch bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    weights_path = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)

    model = build_model(DEFAULT_CLS)
    state = torch.load(str(weights_path), map_location="cpu")
    model.load_state_dict(state.get("model_state_dict", state))
    model.eval()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    series = load_series(case_dir)
    D = len(series.image_ids)
    input_sz = DEFAULT_CLS.input_size  # 384

    cls_rows: list[dict] = []
    all_probs: list[np.ndarray] = []

    with torch.no_grad():
        for z, image_id in enumerate(series.image_ids):
            hu_slice = series.hu[z]
            img = hu_to_three_channel(hu_slice, DEFAULT_WINDOWS)  # (H, W, 3) float32 [0,1]
            x = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(device)  # (1, 3, H, W)
            x = F.interpolate(x, size=(input_sz, input_sz), mode="bilinear", align_corners=False)
            logits = model(x).squeeze(0)  # (num_classes,)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_probs.append(probs)
            for class_id, prob in enumerate(probs):
                cls_rows.append({"image_id": image_id, "class_id": class_id, "probability": float(prob)})

    # Vaka-düzeyi: ortalama olasılık
    if all_probs:
        avg_probs = np.mean(all_probs, axis=0)
        for class_id, prob in enumerate(avg_probs):
            cls_rows.append({"image_id": None, "class_id": class_id, "probability": float(prob)})

    return ArchitectureOutput(bbox_rows=[], cls_rows=cls_rows)


def _predict_organ_bag_transformer(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    """OBT: çok-görevli — FCOS bbox (dilim-düzeyi) + hasta-düzeyi sınıflandırma."""
    try:
        import numpy as np
        import torch
        from src.organ_bag_transformer import (
            OrganBagTransformer, OBTConfig, ANATOMICAL_DEFAULT_Z_FRACS,
            decode_fcos_output, N_CLASSES,
        )
        from src.config import DEFAULT_WINDOWS
        from src.dicom_utils import load_series, hu_to_three_channel
    except ImportError as exc:
        raise MLDependencyUnavailable(
            "timm/torch bu ortamda kurulu değil (GPU sunucusu gerekir)"
        ) from exc

    storage = get_storage_backend()
    weights_path = storage.local_path(model_version.weights_storage_key)
    case_dir = storage.local_path(case.storage_key)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cfg = OBTConfig(encoder_pretrained=False)  # ağırlıkları checkpoint'ten yükleyeceğiz
    model = OrganBagTransformer(cfg).to(device)
    state = torch.load(str(weights_path), map_location="cpu")
    model.load_state_dict(state.get("model_state_dict", state))
    model.eval()

    series = load_series(case_dir)
    D = len(series.image_ids)

    # Tüm dilimleri (3, H, W) numpy array olarak hazırla
    imgs = np.stack([
        hu_to_three_channel(series.hu[z], DEFAULT_WINDOWS).transpose(2, 0, 1)
        for z in range(D)
    ])  # (D, 3, H, W) float32 [0, 1]

    BATCH = 8

    # 1) Tüm dilimleri encode et → slice_features (D, d_model, H', W')
    all_features: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, D, BATCH):
            batch = torch.from_numpy(imgs[start:start + BATCH]).to(device)
            feats = model.encode_slices(batch)  # (B, d_model, H', W')
            all_features.append(feats)
    slice_features = torch.cat(all_features, dim=0)  # (D, d_model, H', W')

    # 2) z_ranges: anatomik varsayılan fraksiyonlardan
    z_ranges = {
        organ_idx: (int(frac_s * D), min(int(frac_e * D), D - 1))
        for organ_idx, (frac_s, frac_e) in ANATOMICAL_DEFAULT_Z_FRACS.items()
    }

    # 3) case_forward → enriched_tokens + patient_logits (sınıflandırma)
    with torch.no_grad():
        enriched, _attn, patient_logits = model.case_forward(slice_features, z_ranges)
        patient_probs = patient_logits.sigmoid().cpu().numpy()

    cls_rows: list[dict] = [
        {"image_id": None, "class_id": c, "probability": float(patient_probs[c])}
        for c in range(N_CLASSES)
    ]

    # 4) fcos_forward → dilim-düzeyi bbox
    bbox_rows: list[dict] = []
    with torch.no_grad():
        for start in range(0, D, BATCH):
            end = min(start + BATCH, D)
            batch = torch.from_numpy(imgs[start:end]).to(device)
            cls_logits, reg_ltrb, centerness = model.fcos_forward(batch, enriched)
            for bi in range(end - start):
                image_id = series.image_ids[start + bi]
                detections = decode_fcos_output(
                    cls_logits[bi:bi + 1], reg_ltrb[bi:bi + 1], centerness[bi:bi + 1],
                    score_thr=conf_threshold,
                )
                for det in detections:
                    bbox_rows.append({
                        "image_id": image_id,
                        "class": det["class"],
                        "x1": det["box"][0], "y1": det["box"][1],
                        "x2": det["box"][2], "y2": det["box"][3],
                        "score": det["score"],
                    })

    return ArchitectureOutput(bbox_rows=bbox_rows, cls_rows=cls_rows)


# ---------------------------------------------------------------------------
# Handler tablosu
# ---------------------------------------------------------------------------

_ARCHITECTURE_HANDLERS: dict[str, object] = {
    "yolo_det":               _predict_yolo_det,
    "yolo_seg":               _predict_yolo_seg,
    "nnunet":                 _predict_nnunet,
    "cls_timm":               _predict_cls_timm,
    "organ_bag_transformer":  _predict_organ_bag_transformer,
}


def run_architecture_inference(
    model_version: ModelVersion, case: Case, conf_threshold: float, min_slice_run: int
) -> ArchitectureOutput:
    """Mimariye göre uygun handler'ı çağırır ve ArchitectureOutput döner."""
    handler = _ARCHITECTURE_HANDLERS.get(model_version.architecture)
    if handler is None:
        raise MLDependencyUnavailable(
            f"'{model_version.architecture}' mimarisi için inference sarmalayıcısı henüz yazılmadı "
            "(plan Bölüm 4 tablosu)"
        )
    return handler(model_version, case, conf_threshold, min_slice_run)


# ---------------------------------------------------------------------------
# Tahmin yazma yardımcıları
# ---------------------------------------------------------------------------

def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ix1, iy1 = max(a[0], b[0]), max(a[1], b[1])
    ix2, iy2 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
    area_b = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def write_predictions_and_group(
    db: Session,
    *,
    case_id,
    model_output: ModelOutput,
    rows: list[dict],
    iou_threshold: float = 0.3,
) -> int:
    """`bbox_rows`'ı annotations + annotation_groups olarak yazar.

    rows: [{"image_id": int, "class": int, "x1":, "y1":, "x2":, "y2":, "score":}]
    image_id'ye göre sıralı olmalı."""
    rows = sorted(rows, key=lambda r: (int(r["class"]), int(r["image_id"])))
    created = 0
    i = 0
    while i < len(rows):
        run_rows = [rows[i]]
        j = i + 1
        while (
            j < len(rows)
            and rows[j]["class"] == rows[i]["class"]
            and int(rows[j]["image_id"]) - int(run_rows[-1]["image_id"]) == 1
            and _iou(
                (run_rows[-1]["x1"], run_rows[-1]["y1"], run_rows[-1]["x2"], run_rows[-1]["y2"]),
                (rows[j]["x1"], rows[j]["y1"], rows[j]["x2"], rows[j]["y2"]),
            ) >= iou_threshold
        ):
            run_rows.append(rows[j])
            j += 1

        group = None
        if len(run_rows) > 1:
            group = AnnotationGroup(
                case_id=case_id,
                class_type="lesion",
                class_id=int(run_rows[0]["class"]),
                geometry_type="bbox",
                source="prediction",
                model_output_id=model_output.id,
                z_start=int(run_rows[0]["image_id"]),
                z_end=int(run_rows[-1]["image_id"]),
                n_slices=len(run_rows),
            )
            db.add(group)
            db.flush()

        for r in run_rows:
            db.add(Annotation(
                case_id=case_id,
                image_id=int(r["image_id"]),
                class_type="lesion",
                class_id=int(r["class"]),
                geometry_type="bbox",
                geometry={"x1": r["x1"], "y1": r["y1"], "x2": r["x2"], "y2": r["y2"]},
                source="prediction",
                confidence=r.get("score"),
                model_output_id=model_output.id,
                group_id=group.id if group else None,
            ))
            created += 1
        i = j

    return created


def write_classification_predictions(
    db: Session,
    *,
    case_id,
    model_output: ModelOutput,
    cls_rows: list[dict],
) -> int:
    """cls_rows → classification_predictions tablosuna yazar.

    cls_rows: [{"image_id": int|None, "class_id": int, "probability": float}]
    image_id=None → vaka-seviyesi tahmin."""
    created = 0
    for row in cls_rows:
        db.add(ClassificationPrediction(
            case_id=case_id,
            image_id=row.get("image_id"),
            model_output_id=model_output.id,
            class_id=row["class_id"],
            probability=row["probability"],
        ))
        created += 1
    return created


def _update_batch_status(db: Session, batch_id) -> None:
    batch = db.get(InferenceBatch, batch_id)
    if batch is None:
        return
    runs = db.execute(select(InferenceRun).where(InferenceRun.batch_id == batch_id)).scalars().all()
    if any(r.status in ("queued", "running") for r in runs):
        return
    statuses = {r.status for r in runs}
    if statuses == {"succeeded"}:
        batch.status = "succeeded"
    elif statuses == {"failed"}:
        batch.status = "failed"
    else:
        batch.status = "partial"
    db.add(batch)
    db.commit()


# ---------------------------------------------------------------------------
# Batch oluşturma (API router + dicom_ingest.py otomatik tetiklemesi)
# ---------------------------------------------------------------------------

def create_inference_batch(
    db: Session, *, case: Case, batch_type: str, model_versions: list[ModelVersion], actor_id
) -> InferenceBatch | None:
    if not model_versions:
        return None

    batch = InferenceBatch(case_id=case.id, batch_type=batch_type, triggered_by=actor_id, status="queued")
    db.add(batch)
    db.flush()

    queue = get_queue()
    for mv in model_versions:
        run = InferenceRun(
            batch_id=batch.id, case_id=case.id, model_version_id=mv.id,
            conf_threshold=0.2, min_slice_run=3, status="queued",
        )
        db.add(run)
        db.flush()
        job = queue.enqueue(run_inference_job, str(run.id))
        run.queue_job_id = job.id
        db.add(run)

    db.commit()
    return batch


def trigger_default_inference(db: Session, *, case: Case, actor_id) -> InferenceBatch | None:
    """Case `ready` olunca otomatik çağrılır. Aktif `run_mode='default'` model
    yoksa sessizce None döner."""
    model_versions = list(
        db.execute(
            select(ModelVersion).where(ModelVersion.run_mode == "default", ModelVersion.status == "active")
        ).scalars().all()
    )
    return create_inference_batch(db, case=case, batch_type="default", model_versions=model_versions, actor_id=actor_id)


# ---------------------------------------------------------------------------
# RQ job giriş noktası
# ---------------------------------------------------------------------------

def run_inference_job(inference_run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(InferenceRun, inference_run_id)
        if run is None:
            logger.error("run_inference_job: run bulunamadı id=%s", inference_run_id)
            return

        run.status = "running"
        db.add(run)
        db.commit()

        case = db.get(Case, run.case_id)
        model_version = db.get(ModelVersion, run.model_version_id)

        try:
            output = run_architecture_inference(
                model_version, case, float(run.conf_threshold), int(run.min_slice_run)
            )

            if output.bbox_rows:
                bbox_output = next(
                    (o for o in model_version.outputs if o.output_type == "bbox"), None
                )
                if bbox_output is None:
                    raise MLDependencyUnavailable(
                        f"Model '{model_version.name}' için 'bbox' tipinde model_output tanımlı değil"
                    )
                write_predictions_and_group(
                    db, case_id=case.id, model_output=bbox_output, rows=output.bbox_rows
                )

            if output.cls_rows:
                cls_output = next(
                    (o for o in model_version.outputs if o.output_type == "classification"), None
                )
                if cls_output is None:
                    raise MLDependencyUnavailable(
                        f"Model '{model_version.name}' için 'classification' tipinde model_output tanımlı değil"
                    )
                write_classification_predictions(
                    db, case_id=case.id, model_output=cls_output, cls_rows=output.cls_rows
                )

            run.status = "succeeded"
            db.add(run)
            db.commit()

        except MLDependencyUnavailable as exc:
            run.status = "failed"
            run.error_message = str(exc)
            db.add(run)
            db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.exception("run_inference_job hata: run=%s", inference_run_id)
            run.status = "failed"
            run.error_message = str(exc)[:1000]
            db.add(run)
            db.commit()

        _update_batch_status(db, run.batch_id)
    finally:
        db.close()
