"""
Makaleye uyumlu değerlendirme:
  F1 @ IoU ∈ {0.1, 0.2, 0.3, 0.4, 0.5}; en yüksek 5 F1'in ortalaması.

Ana sınıf: Evaluator — ground-truth DataFrame'i tutarak tüm metrik
hesaplamalarına tek arayüz sağlar.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from .config import SUPER_CLASSES


def _iou_xyxy(a: Sequence[float], b: Sequence[float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    ua = max(0.0, (ax2 - ax1) * (ay2 - ay1))
    ub = max(0.0, (bx2 - bx1) * (by2 - by1))
    return inter / max(ua + ub - inter, 1e-6)


def f1_at_iou(pred: pd.DataFrame,
              gt: pd.DataFrame,
              iou_th: float) -> Dict[str, float]:
    """
    pred/gt şeması: columns=[case, image_id, class, x1, y1, x2, y2, score (pred)].
    Sınıf-başına ve makro F1 döner.
    """
    classes = sorted(set(pred["class"]).union(set(gt["class"])))
    per_cls = {}
    tp_total, fp_total, fn_total = 0, 0, 0
    for cls in classes:
        p = pred[pred["class"] == cls]
        g = gt[gt["class"] == cls]
        tp, fp, fn = _match(p, g, iou_th)
        tp_total += tp; fp_total += fp; fn_total += fn
        prec = tp / max(tp + fp, 1)
        rec = tp / max(tp + fn, 1)
        f1 = 2 * prec * rec / max(prec + rec, 1e-9)
        per_cls[cls] = {"precision": prec, "recall": rec, "f1": f1,
                        "tp": tp, "fp": fp, "fn": fn}
    macro_f1 = float(np.mean([v["f1"] for v in per_cls.values()])) if per_cls else 0.0
    micro_p = tp_total / max(tp_total + fp_total, 1)
    micro_r = tp_total / max(tp_total + fn_total, 1)
    micro_f1 = 2 * micro_p * micro_r / max(micro_p + micro_r, 1e-9)
    return {"per_class": per_cls, "macro_f1": macro_f1, "micro_f1": micro_f1}


def _match(pred: pd.DataFrame, gt: pd.DataFrame, iou_th: float) -> Tuple[int, int, int]:
    """Greedy, per-image matching (skor'a göre sıralı pred)."""
    tp = fp = 0
    matched = set()                 # (case, image_id, gt_index)
    pred = pred.sort_values("score", ascending=False) if "score" in pred.columns else pred
    gt_group = gt.groupby(["case", "image_id"])

    for _, pr in pred.iterrows():
        key = (pr["case"], pr["image_id"])
        if key not in gt_group.groups:
            fp += 1
            continue
        cand = gt_group.get_group(key)
        best_iou, best_idx = 0.0, -1
        for idx, g in cand.iterrows():
            if (pr["case"], pr["image_id"], idx) in matched:
                continue
            iou = _iou_xyxy((pr["x1"], pr["y1"], pr["x2"], pr["y2"]),
                            (g["x1"], g["y1"], g["x2"], g["y2"]))
            if iou > best_iou:
                best_iou, best_idx = iou, idx
        if best_iou >= iou_th:
            tp += 1
            matched.add((pr["case"], pr["image_id"], best_idx))
        else:
            fp += 1

    total_gt = len(gt)
    fn = total_gt - len(matched)
    return tp, fp, fn


def top5_f1_mean(pred: pd.DataFrame, gt: pd.DataFrame,
                 thresholds: Sequence[float] = (0.1, 0.2, 0.3, 0.4, 0.5)) -> Dict:
    """Makaleye uyumlu tek skalar: top-5 F1 ortalaması."""
    f1s = []
    for th in thresholds:
        r = f1_at_iou(pred, gt, th)
        f1s.append((th, r["macro_f1"]))
    f1s_sorted = sorted(f1s, key=lambda x: x[1], reverse=True)
    top5 = f1s_sorted[:5]
    return {
        "per_threshold": f1s,
        "top5": top5,
        "top5_mean_f1": float(np.mean([v for _, v in top5])),
    }


# ---------------------------------------------------------------------------
# EVALUATOR (üst düzey API)
# ---------------------------------------------------------------------------
class Evaluator:
    """
    Ground-truth DataFrame'i tutarak tüm metrik hesaplamalarına tek arayüz.

    Kullanım:
        ev = Evaluator(gt_df)
        print(ev.top5_f1(pred_df))
        print(ev.patient_level(pred_df))
        print(ev.compare({"yolo": pred_yolo, "nnunet": pred_nnunet}))

    gt_df / pred_df şeması:
        case (int|str), image_id (int), class (int),
        x1, y1, x2, y2 (piksel); pred_df ayrıca score (float) içerir.
    """

    def __init__(
        self,
        gt_df: pd.DataFrame,
        classes: List[str] | None = None,
    ) -> None:
        self.gt = gt_df
        self.classes = classes if classes is not None else SUPER_CLASSES

    # ------------------------------------------------------------------
    # Temel metrikler
    # ------------------------------------------------------------------
    def top5_f1(self, pred_df: pd.DataFrame) -> float:
        """Makaleye uyumlu tek skalarlı skor: top-5 IoU eşiğindeki makro-F1 ort."""
        return top5_f1_mean(pred_df, self.gt)["top5_mean_f1"]

    def f1_at_iou(self, pred_df: pd.DataFrame, iou_th: float = 0.3) -> Dict:
        """
        Belirli bir IoU eşiğinde per-sınıf + makro/mikro F1.

        Dönen sözlük: {per_class: {cls: {precision, recall, f1, tp, fp, fn}},
                       macro_f1, micro_f1}
        """
        return f1_at_iou(pred_df, self.gt, iou_th)

    # ------------------------------------------------------------------
    # Hasta düzeyi analiz
    # ------------------------------------------------------------------
    def patient_level(self, pred_df: pd.DataFrame) -> pd.DataFrame:
        """
        Per-sınıf hasta düzeyi binary F1 (bir vakada patoloji var/yok).

        Her sınıf için: vaka bazında TP/FP/FN; sınıf başına precision, recall, f1.
        Dönen DataFrame'e ek olarak 'macro_f1' sütunu (tüm sınıf ortalaması) eklenir.
        """
        rows = []
        for cls_id, cls_name in enumerate(self.classes):
            gt_cases = set(self.gt[self.gt["class"] == cls_id]["case"].unique())
            pred_cases = (
                set(pred_df[pred_df["class"] == cls_id]["case"].unique())
                if not pred_df.empty else set()
            )
            tp = len(gt_cases & pred_cases)
            fp = len(pred_cases - gt_cases)
            fn = len(gt_cases - pred_cases)
            prec = tp / max(tp + fp, 1)
            rec = tp / max(tp + fn, 1)
            f1 = 2 * prec * rec / max(prec + rec, 1e-9)
            rows.append({
                "class": cls_name,
                "tp": tp, "fp": fp, "fn": fn,
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1": round(f1, 4),
            })
        result = pd.DataFrame(rows)
        result["macro_f1"] = round(float(result["f1"].mean()), 4)
        return result

    # ------------------------------------------------------------------
    # Model karşılaştırma
    # ------------------------------------------------------------------
    def compare(self, models: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Birden fazla modeli top5_f1 metriğiyle karşılaştırır.

        models: {"model_adı": pred_df, ...}
        Dönen DataFrame: model, top5_f1 sütunları; skora göre azalan sıra.
        """
        rows = []
        for name, pred_df in models.items():
            result = top5_f1_mean(pred_df, self.gt)
            rows.append({
                "model": name,
                "top5_f1": round(result["top5_mean_f1"], 4),
                "best_iou_th": result["top5"][0][0] if result["top5"] else None,
                "best_f1": round(result["top5"][0][1], 4) if result["top5"] else None,
            })
        return (
            pd.DataFrame(rows)
            .sort_values("top5_f1", ascending=False)
            .reset_index(drop=True)
        )
