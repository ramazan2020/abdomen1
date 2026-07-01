"""TR_ABDOMEN_RAD_EMERGENCY analiz paketi."""
from __future__ import annotations

import importlib
from typing import Any

__version__ = "0.1.0"

__all__ = [
    # pipeline sınıfları
    "DicomVolume",
    "BboxLifter",
    "NnUNetPipeline",
    "YoloPipeline",
    "Evaluator",
    # veri hazırlığı
    "build_manifest",
    "export_slices",
    # config
    "DEFAULT_DET",
    "DEFAULT_SEG",
    "DEFAULT_SPLIT",
    "SUPER_CLASSES",
    "DetConfig",
    "SegConfig",
    "SplitConfig",
    "Window",
    # OrganBagTransformer
    "OBTConfig",
    "OBTLoss",
    "OrganBagTransformer",
    "build_z_ranges_from_annotations",
    "compute_triage_score",
    "compute_uncertainty",
    "decode_fcos_output",
]

# Bu sembollerin hangi alt modülden geldiğini belirtir; gerçek import, sembol
# `src.X` olarak erişilene kadar ertelenir (PEP 562 modül-seviyesi __getattr__).
#
# Neden: `src.organ_bag_transformer` ve `src.detection`/`src.nnunet`/`src.evaluation`/
# `src.lifting`/`src.preprocessing` modül-seviyesinde torch/pandas/tqdm import ediyor.
# Bunlar olmadan da (örn. webapp backend'inde) `from src.dicom_utils import ...` gibi
# tek bir alt modülü kullanabilmek için paketin __init__.py'ı bu ağır bağımlılıkları
# *her zaman* tetiklememeli — aksi halde "ultralytics/torch fonksiyon içinde lazy
# import edilir" deseni, paket importu seviyesinde anlamsızlaşır.
_LAZY_ATTRS: dict[str, str] = {
    "DEFAULT_DET": ".config",
    "DEFAULT_SEG": ".config",
    "DEFAULT_SPLIT": ".config",
    "SUPER_CLASSES": ".config",
    "DetConfig": ".config",
    "SegConfig": ".config",
    "SplitConfig": ".config",
    "Window": ".config",
    "YoloPipeline": ".detection",
    "OBTConfig": ".organ_bag_transformer",
    "OBTLoss": ".organ_bag_transformer",
    "OrganBagTransformer": ".organ_bag_transformer",
    "build_z_ranges_from_annotations": ".organ_bag_transformer",
    "compute_triage_score": ".organ_bag_transformer",
    "compute_uncertainty": ".organ_bag_transformer",
    "decode_fcos_output": ".organ_bag_transformer",
    "DicomVolume": ".dicom_utils",
    "Evaluator": ".evaluation",
    "BboxLifter": ".lifting",
    "NnUNetPipeline": ".nnunet",
    "build_manifest": ".preprocessing",
    "export_slices": ".preprocessing",
}


def __getattr__(name: str) -> Any:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target, __name__)
    value = getattr(module, name)
    globals()[name] = value  # sonraki erişimler doğrudan değeri bulsun, tekrar import etmesin
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_LAZY_ATTRS))
