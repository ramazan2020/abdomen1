"""
Makaleye uyumlu değerlendirme:
  F1 @ IoU ∈ {0.1, 0.2, 0.3, 0.4, 0.5}; en yüksek 5 F1'in ortalaması.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd


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
