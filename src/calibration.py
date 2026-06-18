"""
Kalibrasyon, eşik optimizasyonu ve seçici tahmin araçları.

Bölüm B katkıları:
  • ece_score              — Beklenen Kalibrasyon Hatası (ECE)
  • brier_score            — Brier skoru (multi-label)
  • reliability_diagram    — görselleştirme için bin istatistikleri
  • TemperatureScaler      — sıcaklık ölçekleme kalibrasyon modeli
  • find_optimal_thresholds— sınıf başına F1 maksimizasyonu

Bölüm D katkıları:
  • entropy_uncertainty    — Shannon entropi (belirsizlik skoru)
  • risk_coverage_curve    — seçici tahmin risk-kapsama eğrisi
  • selective_metrics      — farklı kapsama düzeylerinde metrikler

Kullanım (Faz5 notebook'ta):
    from src.calibration import (
        ece_score, brier_score, TemperatureScaler,
        find_optimal_thresholds, risk_coverage_curve,
    )
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn


# ───────────────────────────────────────────────────────────────────────────
# ECE + Brier
# ───────────────────────────────────────────────────────────────────────────

def ece_score(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
) -> float:
    """
    Beklenen Kalibrasyon Hatası (ECE) — multi-label için makro ortalama.

    Parameters
    ----------
    probs  : (N, C) float — sigmoid çıkışlar
    labels : (N, C) int  — 0/1
    n_bins : kalibrasyon bin sayısı

    Returns
    -------
    ece : float ∈ [0, 1]
    """
    probs  = np.asarray(probs,  dtype=np.float64)
    labels = np.asarray(labels, dtype=np.float64)
    N, C   = probs.shape
    ece_per_class = []
    bins = np.linspace(0, 1, n_bins + 1)
    for c in range(C):
        p, y  = probs[:, c], labels[:, c]
        total, weighted = 0.0, 0.0
        for lo, hi in zip(bins[:-1], bins[1:]):
            mask = (p >= lo) & (p < hi)
            if mask.sum() == 0:
                continue
            acc  = y[mask].mean()
            conf = p[mask].mean()
            n_b  = mask.sum()
            weighted += n_b * abs(acc - conf)
            total    += n_b
        ece_per_class.append(weighted / max(total, 1))
    return float(np.mean(ece_per_class))


def brier_score(
    probs: np.ndarray,
    labels: np.ndarray,
) -> float:
    """
    Multi-label Brier skoru: mean squared error across all sınıflar.

    Returns
    -------
    brier : float ∈ [0, 2]  (düşük = iyi)
    """
    p = np.asarray(probs,  dtype=np.float64)
    y = np.asarray(labels, dtype=np.float64)
    return float(np.mean((p - y) ** 2))


def reliability_diagram(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
    class_idx: int = 0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Tek sınıf için güvenilirlik diyagramı istatistikleri.

    Returns
    -------
    bin_centers, bin_accuracy, bin_count
    """
    p  = np.asarray(probs[:, class_idx],  dtype=np.float64)
    y  = np.asarray(labels[:, class_idx], dtype=np.float64)
    bins = np.linspace(0, 1, n_bins + 1)
    centers, accs, counts = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (p >= lo) & (p < hi)
        centers.append((lo + hi) / 2)
        accs.append(y[mask].mean() if mask.sum() > 0 else 0.0)
        counts.append(int(mask.sum()))
    return np.array(centers), np.array(accs), np.array(counts)


# ───────────────────────────────────────────────────────────────────────────
# Sıcaklık Ölçekleme
# ───────────────────────────────────────────────────────────────────────────

class TemperatureScaler(nn.Module):
    """
    Guo et al. 2017 — tek parametreli kalibrasyon.
    Logit'leri T ile böler; büyük T daha düzgün (calibrated) olasılıklar verir.

    Kullanım:
        scaler = TemperatureScaler()
        scaler.fit(logits_np, labels_np)
        calibrated_probs = scaler.calibrate(logits_np)
    """

    def __init__(self, init_T: float = 1.0) -> None:
        super().__init__()
        self.temperature = nn.Parameter(torch.tensor(init_T))

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature.clamp(min=0.01)

    def fit(
        self,
        logits: np.ndarray,
        labels: np.ndarray,
        lr: float = 0.01,
        max_iter: int = 500,
    ) -> float:
        """NLL minimizasyonuyla sıcaklığı bul. Optimal T'yi döner."""
        logits_t = torch.tensor(logits, dtype=torch.float32)
        labels_t = torch.tensor(labels, dtype=torch.float32)
        optimizer = torch.optim.LBFGS(
            [self.temperature], lr=lr, max_iter=max_iter, line_search_fn="strong_wolfe"
        )

        def _closure():
            optimizer.zero_grad()
            loss = nn.functional.binary_cross_entropy_with_logits(
                self(logits_t), labels_t
            )
            loss.backward()
            return loss

        optimizer.step(_closure)
        return float(self.temperature.item())

    def calibrate(self, logits: np.ndarray) -> np.ndarray:
        """Logit'leri (N, C) → kalibre edilmiş olasılıklar (N, C)."""
        with torch.no_grad():
            out = torch.sigmoid(self(torch.tensor(logits, dtype=torch.float32)))
        return out.numpy()

    def save(self, path) -> None:
        torch.save({"temperature": self.temperature.item()}, path)

    @classmethod
    def load(cls, path) -> "TemperatureScaler":
        state = torch.load(path, map_location="cpu")
        obj = cls(init_T=state["temperature"])
        return obj


# ───────────────────────────────────────────────────────────────────────────
# Eşik Optimizasyonu (sınıf başına F1 maksimizasyonu)
# ───────────────────────────────────────────────────────────────────────────

def find_optimal_thresholds(
    probs: np.ndarray,
    labels: np.ndarray,
    class_names: Optional[List[str]] = None,
    n_thresholds: int = 200,
) -> Dict[str, float]:
    """
    Her sınıf için bağımsız F1 maksimizasyonu.

    Parameters
    ----------
    probs       : (N, C) float
    labels      : (N, C) int
    class_names : sınıf adları (None → "class_0", ...)
    n_thresholds: aranacak eşik sayısı

    Returns
    -------
    thresholds : {class_name: optimal_threshold}
    """
    probs  = np.asarray(probs,  dtype=np.float64)
    labels = np.asarray(labels, dtype=np.float64)
    N, C   = probs.shape
    if class_names is None:
        class_names = [f"class_{i}" for i in range(C)]

    ts = np.linspace(0.01, 0.99, n_thresholds)
    result = {}
    for c, name in enumerate(class_names):
        p, y    = probs[:, c], labels[:, c]
        best_t  = 0.5
        best_f1 = -1.0
        for t in ts:
            pred = (p >= t).astype(float)
            tp   = (pred * y).sum()
            fp   = (pred * (1 - y)).sum()
            fn   = ((1 - pred) * y).sum()
            f1   = (2 * tp) / max(2 * tp + fp + fn, 1e-9)
            if f1 > best_f1:
                best_f1 = f1
                best_t  = t
        result[name] = float(best_t)
    return result


def apply_thresholds(
    probs: np.ndarray,
    thresholds: Dict[str, float],
    class_names: List[str],
) -> np.ndarray:
    """
    Sınıf başına eşik uygular.

    Returns
    -------
    preds : (N, C) int
    """
    N, C  = probs.shape
    preds = np.zeros((N, C), dtype=np.int32)
    for c, name in enumerate(class_names):
        t = thresholds.get(name, 0.5)
        preds[:, c] = (probs[:, c] >= t).astype(int)
    return preds


# ───────────────────────────────────────────────────────────────────────────
# Seçici Tahmin (Bölüm D)
# ───────────────────────────────────────────────────────────────────────────

def entropy_uncertainty(probs: np.ndarray) -> np.ndarray:
    """
    Shannon entropisi — hasta başına belirsizlik skoru.

    probs  : (N, C) float ∈ (0, 1)
    Returns: (N,) float — düşük=emin, yüksek=belirsiz
    """
    p   = np.clip(probs, 1e-9, 1.0 - 1e-9)
    p1  = p
    p0  = 1.0 - p
    return -(p1 * np.log(p1) + p0 * np.log(p0)).mean(axis=1)


def risk_coverage_curve(
    probs: np.ndarray,
    labels: np.ndarray,
    uncertainty: Optional[np.ndarray] = None,
    class_names: Optional[List[str]] = None,
    n_thresholds: int = 100,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Risk-kapsama eğrisi — seçici tahmin değerlendirmesi.

    Yüksek belirsizlikli vakaları dışarıda bırakarak kalan vakalar
    üzerindeki hatayı (risk) ve kapsama oranını hesaplar.

    Parameters
    ----------
    probs       : (N, C) — sigmoid olasılıkları
    labels      : (N, C) — 0/1 etiketler
    uncertainty : (N,) — belirsizlik skoru (None → entropy kullanılır)
    n_thresholds: kaç farklı kapsama eşiği denensin

    Returns
    -------
    coverage : (n_thresholds,)  — kapsama oranı [0, 1]
    risk     : (n_thresholds,)  — hata oranı (1 - macro F1)
    n_covered: (n_thresholds,)  — kapsanan vaka sayısı
    """
    probs  = np.asarray(probs,  dtype=np.float64)
    labels = np.asarray(labels, dtype=np.float64)
    N, C   = probs.shape

    if uncertainty is None:
        uncertainty = entropy_uncertainty(probs)

    opt_t = find_optimal_thresholds(probs, labels, class_names)
    class_names = class_names or [f"class_{i}" for i in range(C)]
    preds_all = apply_thresholds(probs, opt_t, class_names)

    # Belirsizliğe göre sırala (düşük belirsizlik = güvenli)
    order  = np.argsort(uncertainty)          # ascending: emin → belirsiz
    thrs   = np.linspace(0, 1, n_thresholds)  # coverage eşikleri

    coverages, risks, n_covered = [], [], []
    for frac in thrs:
        k = max(1, int(frac * N))
        idx     = order[:k]                   # en emin k vaka
        p_sub   = preds_all[idx]
        y_sub   = labels[idx]
        # Macro F1
        f1s = []
        for c in range(C):
            tp  = (p_sub[:, c] * y_sub[:, c]).sum()
            fp  = (p_sub[:, c] * (1 - y_sub[:, c])).sum()
            fn  = ((1 - p_sub[:, c]) * y_sub[:, c]).sum()
            f1  = (2 * tp) / max(2 * tp + fp + fn, 1e-9)
            f1s.append(f1)
        macro_f1 = float(np.mean(f1s))
        coverages.append(frac)
        risks.append(1.0 - macro_f1)
        n_covered.append(k)

    return np.array(coverages), np.array(risks), np.array(n_covered)


# ───────────────────────────────────────────────────────────────────────────
# Ensemble Ortalaması
# ───────────────────────────────────────────────────────────────────────────

def ensemble_average(
    probs_list: List[np.ndarray],
    weights: Optional[np.ndarray] = None,
) -> np.ndarray:
    """
    Birden fazla fold modelinin olasılıklarını ağırlıklı ortalama ile birleştirir.

    probs_list : list of (N, C) arrays
    weights    : (K,) normalleştirilmiş ağırlıklar (None → eşit ağırlık)

    Returns: (N, C)
    """
    K = len(probs_list)
    if weights is None:
        weights = np.ones(K) / K
    weights = np.asarray(weights, dtype=np.float64)
    weights = weights / weights.sum()
    stack   = np.stack(probs_list, axis=0)    # (K, N, C)
    return (stack * weights[:, None, None]).sum(axis=0)
