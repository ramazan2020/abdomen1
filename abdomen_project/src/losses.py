"""Class-balanced BCE ve Focal loss varyantları."""
from __future__ import annotations

from typing import Sequence

import torch
import torch.nn.functional as F
from torch import nn


class FocalBCE(nn.Module):
    """Sigmoid + Focal (Lin et al., 2017). Multi-label uyumlu."""

    def __init__(self, gamma: float = 2.0,
                 alpha: Sequence[float] | torch.Tensor | None = None,
                 reduction: str = "mean"):
        super().__init__()
        self.gamma = gamma
        if alpha is not None:
            if not isinstance(alpha, torch.Tensor):
                alpha = torch.tensor(alpha, dtype=torch.float32)
            self.register_buffer("alpha", alpha)
        else:
            self.alpha = None
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # logits, targets: (B, C)
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        pt = torch.exp(-bce)                              # probability of true class
        focal = (1 - pt) ** self.gamma * bce
        if self.alpha is not None:
            a = self.alpha.to(logits.device)
            w = targets * a + (1 - targets) * (1 - a)     # pozitif/negatif ayrı ağırlık
            focal = w * focal
        if self.reduction == "mean":
            return focal.mean()
        if self.reduction == "sum":
            return focal.sum()
        return focal


def compute_class_balanced_alpha(pos_counts: Sequence[int],
                                 total: int,
                                 beta: float = 0.9999) -> torch.Tensor:
    """
    Cui et al., 2019 — Effective Number of Samples. `alpha_c = (1-β) / (1 - β^n_c)`
    Pozitif sınıfa verilen ağırlıktır; negatif sınıf için `1 - alpha_c` kullanılır.
    """
    n = torch.tensor(pos_counts, dtype=torch.float64)
    eff_num = 1.0 - beta ** n
    w = (1.0 - beta) / torch.clamp(eff_num, min=1e-8)
    w = w / w.sum() * len(pos_counts)                     # ortalama 1'e normalize
    # [0,1] aralığına sıkıştır: pozitif ağırlığı [0.5..0.95] bandına al
    w = torch.sigmoid(torch.log(w))
    return w.float()
