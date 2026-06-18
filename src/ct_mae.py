"""
CT-MAE: SimMIM tabanlı öz-denetimli CT dilim ön-eğitimi.

Temel prensip (SimMIM, He et al. 2022 uyarlaması):
  • ConvNeXt-S omurga — OBT ile doğrudan uyumlu; ağırlıklar sorunsuz aktarılır.
  • Giriş görüntüsünün rastgele %75'i öğrenilebilir bir maske belirteci (kanal
    başına skaler) ile örtülür; tam görüntü omurga üzerinden işlenir.
  • Tahmin başlığı maskelenen konumlardaki normalize piksel değerlerini yeniden
    üretir; kayıp yalnızca maskelenen yamalar üzerinde L1.

Neden SimMIM (ViT-MAE değil)?
  OBT zaten ConvNeXt-S kullandığından ön-eğitim ağırlıkları mimari değişiklik
  gerektirmeksizin aktarılır; bu K4 katkısının (etiket-verimliliği) temiz
  ablasyonunu sağlar.

Veri sızıntısı disiplini:
  Ön-eğitimde yalnızca train-split dilimleri kullanılır (fold-val + holdout hiçbir
  zaman ön-eğitim havuzuna girmez).

Kullanım:
    from src.ct_mae import CTMaskedAutoencoder, CTMAEConfig
    model = CTMaskedAutoencoder(CTMAEConfig())
    loss, mask = model(imgs)               # ön-eğitim
    feats = model.extract_features(imgs)   # aşağı-akış
    ckpt  = model.get_encoder_state_dict() # OBT'ye aktar
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import timm
    _HAS_TIMM = True
except ImportError:
    _HAS_TIMM = False


@dataclass
class CTMAEConfig:
    # ── Omurga ──────────────────────────────────────────────────────────
    backbone: str = "convnext_small.fb_in22k_ft_in1k"
    pretrained_backbone: bool = False   # ön-eğitimde ImageNet ağırlığı kullanılmaz
    img_size: int = 512                 # CT dilim girişi (H = W)
    patch_stride: int = 32             # ConvNeXt-S toplam downsampling oranı
    backbone_dim: int = 768            # ConvNeXt-S stage-4 kanal sayısı
    # ── Maskeleme ───────────────────────────────────────────────────────
    mask_ratio: float = 0.75
    # ── Tahmin başlığı ──────────────────────────────────────────────────
    pred_hidden: int = 256
    # ── Kayıp ───────────────────────────────────────────────────────────
    norm_pix_loss: bool = True          # yama başına normalize et
    loss_type: str = "l1"               # "l1" | "l2"


class CTMaskedAutoencoder(nn.Module):
    """
    SimMIM tabanlı CT maskelemeli öz-kodlayıcı.

    forward(x)          → (loss, mask_flat)           ön-eğitim modu
    extract_features(x) → (B, backbone_dim, H/32, W/32)  çıkarım modu
    """

    def __init__(self, cfg: CTMAEConfig = CTMAEConfig()) -> None:
        super().__init__()
        if not _HAS_TIMM:
            raise ImportError("timm gerekli: pip install timm")
        self.cfg = cfg
        p = cfg.patch_stride

        # Omurga: ConvNeXt-S
        self.backbone = timm.create_model(
            cfg.backbone,
            pretrained=cfg.pretrained_backbone,
            num_classes=0,
        )

        # Maske belirteci: kanal başına öğrenilebilir skaler
        self.mask_token = nn.Parameter(torch.zeros(1, 3, 1, 1))
        nn.init.normal_(self.mask_token, std=0.02)

        # Tahmin başlığı: (B, D, H/p, W/p) → (B, 3·p², H/p, W/p)
        self.pred_head = nn.Sequential(
            nn.Conv2d(cfg.backbone_dim, cfg.pred_hidden, 1),
            nn.GELU(),
            nn.Conv2d(cfg.pred_hidden, 3 * p * p, 1),
        )

    # ── Dahili yardımcılar ───────────────────────────────────────────────

    def _random_mask(
        self, B: int, n_h: int, n_w: int, device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns
        -------
        mask_flat   : (B, n_patches)  float — 1=maskelendi, 0=görünür
        mask_spatial: (B, 1, n_h, n_w) float
        """
        n = n_h * n_w
        n_mask = int(n * self.cfg.mask_ratio)
        ids = torch.rand(B, n, device=device).argsort(dim=1)
        mask_flat = torch.zeros(B, n, device=device)
        mask_flat.scatter_(1, ids[:, :n_mask], 1.0)
        return mask_flat, mask_flat.reshape(B, 1, n_h, n_w)

    def _patchify(self, x: torch.Tensor) -> torch.Tensor:
        """(B, 3, H, W) → (B, n_patches, 3·p²)"""
        p = self.cfg.patch_stride
        B, C, H, W = x.shape
        n_h, n_w = H // p, W // p
        x = x.reshape(B, C, n_h, p, n_w, p)
        return x.permute(0, 2, 4, 1, 3, 5).reshape(B, n_h * n_w, C * p * p)

    def _backbone_features(self, x: torch.Tensor) -> torch.Tensor:
        """timm NHWC/NCHW farkını soyutlar; her zaman NCHW döner."""
        feats = self.backbone.forward_features(x)
        if feats.ndim == 4 and feats.shape[-1] == self.cfg.backbone_dim:
            feats = feats.permute(0, 3, 1, 2).contiguous()  # NHWC → NCHW
        return feats  # (B, backbone_dim, n_h, n_w)

    # ── İleri geçiş (ön-eğitim) ─────────────────────────────────────────

    def forward(
        self, x: torch.Tensor, mask_ratio: Optional[float] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Parameters
        ----------
        x : (B, 3, H, W)

        Returns
        -------
        loss     : skaler
        mask_flat: (B, n_patches)  — görselleştirme için
        """
        mr = mask_ratio if mask_ratio is not None else self.cfg.mask_ratio
        B, _, H, W = x.shape
        p = self.cfg.patch_stride
        n_h, n_w = H // p, W // p

        # 1. Maske
        mask_flat, mask_sp = self._random_mask(B, n_h, n_w, x.device)
        mask_px = F.interpolate(mask_sp, scale_factor=float(p), mode="nearest")

        # 2. Maskeleme (piksel düzeyinde)
        x_masked = x * (1.0 - mask_px) + self.mask_token * mask_px

        # 3. Omurga kodlaması
        feats = self._backbone_features(x_masked)          # (B, D, n_h, n_w)

        # 4. Tahmin → yama boyutuna yeniden şekillendir
        pred_sp = self.pred_head(feats)                    # (B, 3·p², n_h, n_w)
        pred_patches = (
            pred_sp.reshape(B, 3, p * p, n_h, n_w)
            .permute(0, 3, 4, 1, 2)
            .reshape(B, n_h * n_w, 3 * p * p)
        )

        # 5. Hedef (isteğe bağlı normalize)
        target = self._patchify(x)                         # (B, n_patches, 3·p²)
        if self.cfg.norm_pix_loss:
            mean = target.mean(-1, keepdim=True)
            std  = target.var(-1, keepdim=True).sqrt().clamp(min=1e-6)
            target = (target - mean) / std

        # 6. Kayıp — yalnızca maskelenen yamalar
        if self.cfg.loss_type == "l1":
            err = (pred_patches - target).abs().mean(-1)   # (B, n_patches)
        else:
            err = ((pred_patches - target) ** 2).mean(-1)

        loss = (err * mask_flat).sum() / mask_flat.sum().clamp(min=1)
        return loss, mask_flat

    # ── Çıkarım modu ────────────────────────────────────────────────────

    def extract_features(self, x: torch.Tensor) -> torch.Tensor:
        """Maskeleme olmadan omurga uzamsal çıktısını döner.

        x : (B, 3, H, W)
        →   (B, backbone_dim, H/32, W/32)
        """
        return self._backbone_features(x)

    # ── OBT ağırlık aktarımı ────────────────────────────────────────────

    def get_encoder_state_dict(self) -> dict:
        """OBT'nin encoder'ına yüklenebilecek omurga ağırlıklarını döner."""
        return {k: v.clone() for k, v in self.backbone.state_dict().items()}

    def save_checkpoint(self, path: Path, epoch: int, loss: float) -> None:
        torch.save(
            {
                "epoch": epoch,
                "loss": loss,
                "model": self.state_dict(),
                "cfg": self.cfg,
            },
            path,
        )

    @classmethod
    def from_checkpoint(
        cls, ckpt_path: Path, cfg: Optional[CTMAEConfig] = None
    ) -> "CTMaskedAutoencoder":
        """Checkpoint'ten model yükle."""
        state = torch.load(ckpt_path, map_location="cpu")
        cfg = cfg or state.get("cfg", CTMAEConfig())
        model = cls(cfg)
        model.load_state_dict(state.get("model", state), strict=False)
        return model
