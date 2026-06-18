"""
OrganBagTransformer (OBT) — boundary-slice yönlendirmeli çok-görevli CT modeli.

CT hacmi → ConvNeXt-S dilim kodlayıcı → organ bag çıkarma (boundary-slice)
  → DETR-tarzı organ bag dikkat → cross-organ transformer
  → çok-görevli çıktılar (hasta-düzeyi, dilim-düzeyi, FCOS tespit, triyaj)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    import timm
except ImportError:
    timm = None

from .config import ANATOMICAL_CLASSES, SUPER_CLASSES

# Patoloji sınıfı (SUPER_CLASSES sırası) → anatomik organ indeksi (ANATOMICAL_CLASSES sırası)
# acute_cholecystitis(0)  → Gall bladder(1)
# kidney_ureter_stone(1)  → Kidney-Bladder(3)
# acute_pancreatitis(2)   → Pancreas(2)
# aortic_aneurysm(3)      → Abdominal Aorta(0)
# acute_appendicitis(4)   → appendix(5)
# acute_diverticulitis(5) → Colon(4)
CLASS_TO_ORGAN_IDX: List[int] = [1, 3, 2, 0, 5, 4]

N_ORGANS: int = len(ANATOMICAL_CLASSES)   # 6
N_CLASSES: int = len(SUPER_CLASSES)       # 6

# Boundary anotasyonu olmayan vakalar için anatomik literatür fraksiyon aralıkları
# (z_norm: 0=kranyal, 1=kaudal)
ANATOMICAL_DEFAULT_Z_FRACS: Dict[int, Tuple[float, float]] = {
    0: (0.10, 0.90),  # Abdominal Aorta
    1: (0.30, 0.65),  # Gall bladder
    2: (0.30, 0.60),  # Pancreas
    3: (0.30, 0.85),  # Kidney-Bladder
    4: (0.40, 0.95),  # Colon
    5: (0.55, 0.90),  # appendix
}


@dataclass
class OBTConfig:
    encoder: str = "convnext_small.fb_in22k_ft_in1k"
    d_model: int = 256
    n_cross_organ_heads: int = 8
    n_cross_organ_layers: int = 4
    fcos_stacks: int = 4
    gate_alpha_init: float = 0.0   # 0 → başlangıçta gate etkisiz
    dropout: float = 0.1
    encoder_pretrained: bool = True
    max_z_position: int = 512      # z-pozisyon embedding boyutu


# ---------------------------------------------------------------------------
# Organ Bag Çıkarıcı (veri hazırlama — model değil)
# ---------------------------------------------------------------------------

def build_z_ranges_from_annotations(
    boundary_df: pd.DataFrame,
    case_id: str,
    image_ids_sorted: List[int],
    fallback_z_fracs: Dict[int, Tuple[float, float]] = ANATOMICAL_DEFAULT_Z_FRACS,
) -> Dict[int, Tuple[int, int]]:
    """
    Bilgi.xlsx boundary anotasyonlarından vaka bazlı z-aralıkları üretir.

    boundary_df   : Type=="Boundary Slice" satırları (prefix'li Case Number)
    case_id       : "T_20001" formatı
    image_ids_sorted : vakadaki image_id'leri sıralanmış (manifest'ten)
    fallback_z_fracs : boundary yoksa kullanılacak fraksiyon aralıkları

    Döndürür: {organ_idx: (z_start, z_end)}  — 0-tabanlı dilim indeksi
    """
    D = len(image_ids_sorted)
    id_to_z = {int(img_id): z for z, img_id in enumerate(image_ids_sorted)}
    case_rows = boundary_df[boundary_df["Case Number"] == case_id]
    organ_name_to_idx = {name: i for i, name in enumerate(ANATOMICAL_CLASSES)}

    result: Dict[int, Tuple[int, int]] = {}

    for organ_idx, organ_name in enumerate(ANATOMICAL_CLASSES):
        organ_rows = case_rows[case_rows["Class"] == organ_name]
        z_positions = [
            id_to_z[int(img_id)]
            for img_id in organ_rows["Image Id"]
            if int(img_id) in id_to_z
        ]

        if len(z_positions) >= 2:
            result[organ_idx] = (min(z_positions), max(z_positions))
        elif organ_idx in fallback_z_fracs:
            frac_s, frac_e = fallback_z_fracs[organ_idx]
            result[organ_idx] = (int(frac_s * D), min(int(frac_e * D), D - 1))
        else:
            result[organ_idx] = (0, D - 1)

    return result


# ---------------------------------------------------------------------------
# Organ Bag Dikkat Modülü
# ---------------------------------------------------------------------------

class OrganBagAttention(nn.Module):
    """
    DETR-tarzı: 6 öğrenilebilir organ sorgusu, her biri kendi bag'ine
    cross-attention uygular.

    Girdi : slice_features (D, C, H, W)  + z_ranges {organ_idx: (z_s, z_e)}
    Çıktı : organ_tokens (6, d_model)
            attn_weights {organ_idx: Tensor(1, 1, L_k)}
    """

    def __init__(self, in_channels: int, d_model: int,
                 n_heads: int = 8, dropout: float = 0.1,
                 max_z: int = 512):
        super().__init__()
        self.d_model = d_model
        self.feat_proj = nn.Linear(in_channels, d_model)
        self.organ_queries = nn.Parameter(torch.randn(N_ORGANS, d_model) * 0.02)
        self.z_pos_enc = nn.Embedding(max_z, d_model)
        self.cross_attn = nn.MultiheadAttention(
            d_model, n_heads, dropout=dropout, batch_first=True
        )
        self.norm = nn.LayerNorm(d_model)

    def _bag_to_kv(
        self,
        bag: torch.Tensor,       # (L_k, C, H, W)
        z_start: int,
    ) -> torch.Tensor:
        """Organ bag'i key-value dizisine dönüştürür: (L_k, d_model)"""
        pooled = bag.mean(dim=(-2, -1))           # (L_k, C) — GAP
        proj = self.feat_proj(pooled)              # (L_k, d_model)
        z_idx = torch.arange(
            z_start, z_start + len(bag),
            device=bag.device,
        ).clamp(0, self.z_pos_enc.num_embeddings - 1)
        return proj + self.z_pos_enc(z_idx)        # (L_k, d_model)

    def forward(
        self,
        slice_features: torch.Tensor,              # (D, C, H, W)
        z_ranges: Dict[int, Tuple[int, int]],
    ) -> Tuple[torch.Tensor, Dict[int, Optional[torch.Tensor]]]:
        D = slice_features.shape[0]
        device = slice_features.device
        organ_tokens = []
        attn_weights_out: Dict[int, Optional[torch.Tensor]] = {}

        for k in range(N_ORGANS):
            if k in z_ranges and z_ranges[k] is not None:
                z_s, z_e = z_ranges[k]
                z_s = max(0, int(z_s))
                z_e = min(D - 1, int(z_e))
            else:
                z_s, z_e = 0, D - 1

            bag = slice_features[z_s : z_e + 1]   # (L_k, C, H, W)

            if len(bag) == 0:
                organ_tokens.append(torch.zeros(1, self.d_model, device=device))
                attn_weights_out[k] = None
                continue

            kv = self._bag_to_kv(bag, z_s).unsqueeze(0)      # (1, L_k, d_model)
            q = self.organ_queries[k].view(1, 1, self.d_model) # (1, 1, d_model)

            token, weights = self.cross_attn(q, kv, kv)        # (1,1,d), (1,1,L_k)
            organ_tokens.append(self.norm(token.squeeze(1)))    # (1, d_model)
            attn_weights_out[k] = weights

        organ_tokens_t = torch.cat(organ_tokens, dim=0)         # (6, d_model)
        return organ_tokens_t, attn_weights_out


# ---------------------------------------------------------------------------
# Cross-Organ Transformer
# ---------------------------------------------------------------------------

class CrossOrganTransformer(nn.Module):
    """
    6 organ token arasında pairwise attention öğrenir.
    6×6 attention matrisi → inter-organ ilişki (yorumlanabilirlik).
    """

    def __init__(self, d_model: int, n_heads: int, n_layers: int, dropout: float = 0.1):
        super().__init__()
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,   # pre-norm: küçük dataset için stabil
        )
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=n_layers)
        self.organ_id_emb = nn.Embedding(N_ORGANS, d_model)

    def forward(self, organ_tokens: torch.Tensor) -> torch.Tensor:
        """organ_tokens: (6, d_model) → enriched: (6, d_model)"""
        ids = torch.arange(N_ORGANS, device=organ_tokens.device)
        x = organ_tokens + self.organ_id_emb(ids)   # (6, d_model)
        x = self.transformer(x.unsqueeze(0))         # (1, 6, d_model)
        return x.squeeze(0)                          # (6, d_model)


# ---------------------------------------------------------------------------
# FCOS Tespit Başlığı
# ---------------------------------------------------------------------------

class _ConvBnReLU(nn.Sequential):
    def __init__(self, channels: int):
        super().__init__(
            nn.Conv2d(channels, channels, 3, padding=1, bias=False),
            nn.GroupNorm(32, channels),
            nn.ReLU(inplace=True),
        )


class FCOSHead(nn.Module):
    """
    Anchor-free FCOS tespit başlığı.

    Anatomy gate: enriched_tokens her sınıf için log-olasılık bias ekler.
    gate_alpha (6,): sınıf başına öğrenilebilir ölçek, 0'dan başlar.
    """

    def __init__(self, in_channels: int, d_model: int = 256,
                 n_classes: int = N_CLASSES,
                 n_stacks: int = 4, gate_alpha_init: float = 0.0):
        super().__init__()
        self.n_classes = n_classes
        self.cls_convs = nn.Sequential(*[_ConvBnReLU(in_channels) for _ in range(n_stacks)])
        self.reg_convs = nn.Sequential(*[_ConvBnReLU(in_channels) for _ in range(n_stacks)])
        self.cls_pred  = nn.Conv2d(in_channels, n_classes, 1)
        self.reg_pred  = nn.Conv2d(in_channels, 4, 1)
        self.ctr_pred  = nn.Conv2d(in_channels, 1, 1)
        self.gate_alpha = nn.Parameter(torch.full((n_classes,), gate_alpha_init))
        # d_model → 1 projeksiyon: organ token'ından gate skalar üretir
        self.gate_proj = nn.Linear(d_model, 1, bias=False)

    def forward(
        self,
        feat: torch.Tensor,                              # (B, C, H, W)
        enriched_tokens: Optional[torch.Tensor] = None, # (6, d_model)
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        cls_feat = self.cls_convs(feat)
        reg_feat = self.reg_convs(feat)

        cls_logits = self.cls_pred(cls_feat)         # (B, 6, H, W)
        reg_ltrb   = self.reg_pred(reg_feat).exp()   # (B, 4, H, W) — pozitif için exp
        centerness = self.ctr_pred(reg_feat)         # (B, 1, H, W)

        if enriched_tokens is not None:
            # Her sınıf için ilgili organ token'ından öğrenilebilir gate skalar üret
            organ_idxs = torch.tensor(
                [CLASS_TO_ORGAN_IDX[c] for c in range(self.n_classes)],
                device=enriched_tokens.device,
            )
            relevant = enriched_tokens[organ_idxs]             # (n_classes, d_model)
            gate_probs = torch.sigmoid(self.gate_proj(relevant).squeeze(-1))  # (n_classes,)
            log_gate = torch.log(gate_probs + 1e-6)
            bias = (self.gate_alpha * log_gate).view(1, self.n_classes, 1, 1)
            cls_logits = cls_logits + bias

        return cls_logits, reg_ltrb, centerness


# ---------------------------------------------------------------------------
# Hasta-Düzeyi Başlık
# ---------------------------------------------------------------------------

class OBTPatientHead(nn.Module):
    """Hasta-düzeyi 6-etiket çok-etiket sınıflandırma."""

    def __init__(self, d_model: int, n_classes: int = N_CLASSES, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(d_model * N_ORGANS, d_model),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(d_model, n_classes),
        )

    def forward(self, enriched_tokens: torch.Tensor) -> torch.Tensor:
        """enriched_tokens: (6, d_model) → patient_logits: (n_classes,)"""
        return self.net(enriched_tokens.flatten().unsqueeze(0)).squeeze(0)


# ---------------------------------------------------------------------------
# Ana Model
# ---------------------------------------------------------------------------

class OrganBagTransformer(nn.Module):
    """
    Ana OBT modeli.

    İki kullanım modu:
      fcos_forward(slice_batch)          → Stage 1 dilim-düzeyi eğitim
      case_forward(slice_features, z_ranges) → Stage 2/3 hasta-düzeyi
    """

    def __init__(self, cfg: OBTConfig = OBTConfig()):
        super().__init__()
        self.cfg = cfg

        if timm is None:
            raise ImportError("timm gerekli: pip install timm>=0.9")

        self.encoder = timm.create_model(
            cfg.encoder,
            pretrained=cfg.encoder_pretrained,
            num_classes=0,
            features_only=True,
        )
        enc_channels = self.encoder.feature_info[-1]["num_chs"]  # ConvNeXt-S: 768

        # Kanal projeksiyon: enc_channels → d_model
        self.chan_proj = nn.Sequential(
            nn.Conv2d(enc_channels, cfg.d_model, 1, bias=False),
            nn.BatchNorm2d(cfg.d_model),
            nn.ReLU(inplace=True),
        )

        self.organ_bag_attn = OrganBagAttention(
            in_channels=cfg.d_model,
            d_model=cfg.d_model,
            n_heads=cfg.n_cross_organ_heads,
            dropout=cfg.dropout,
            max_z=cfg.max_z_position,
        )
        self.cross_organ_tf = CrossOrganTransformer(
            d_model=cfg.d_model,
            n_heads=cfg.n_cross_organ_heads,
            n_layers=cfg.n_cross_organ_layers,
            dropout=cfg.dropout,
        )
        self.fcos_head = FCOSHead(
            in_channels=cfg.d_model,
            d_model=cfg.d_model,
            n_stacks=cfg.fcos_stacks,
            gate_alpha_init=cfg.gate_alpha_init,
        )
        self.patient_head = OBTPatientHead(d_model=cfg.d_model)

    def encode_slices(self, x: torch.Tensor) -> torch.Tensor:
        """x: (B, 3, H, W) → (B, d_model, H/32, W/32)"""
        feats = self.encoder(x)
        return self.chan_proj(feats[-1])

    def fcos_forward(
        self,
        slice_batch: torch.Tensor,                       # (B, 3, H, W)
        enriched_tokens: Optional[torch.Tensor] = None,  # (6, d_model)
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Stage 1 eğitimi ve dilim-düzeyi çıkarım."""
        feat = self.encode_slices(slice_batch)
        return self.fcos_head(feat, enriched_tokens)

    def case_forward(
        self,
        slice_features: torch.Tensor,            # (D, d_model, H', W')
        z_ranges: Dict[int, Tuple[int, int]],
    ) -> Tuple[torch.Tensor, Dict[int, Optional[torch.Tensor]], torch.Tensor]:
        """
        Tek vaka için organ bag → cross-organ → hasta kararı.

        Döndürür:
            enriched_tokens : (6, d_model)
            attn_weights    : {organ_idx: Tensor(1,1,L_k) veya None}
            patient_logits  : (n_classes,)
        """
        organ_tokens, attn_weights = self.organ_bag_attn(slice_features, z_ranges)
        enriched = self.cross_organ_tf(organ_tokens)
        patient_logits = self.patient_head(enriched)
        return enriched, attn_weights, patient_logits

    def param_groups(self) -> List[Dict]:
        """3 parametre grubu: encoder (düşük LR), yeni modüller (yüksek LR)."""
        encoder_params = list(self.encoder.parameters()) + list(self.chan_proj.parameters())
        new_params = (
            list(self.organ_bag_attn.parameters())
            + list(self.cross_organ_tf.parameters())
            + list(self.fcos_head.parameters())
            + list(self.patient_head.parameters())
        )
        return [
            {"params": encoder_params, "lr": 1e-5, "name": "encoder"},
            {"params": new_params,     "lr": 1e-3, "name": "new_modules"},
        ]


# ---------------------------------------------------------------------------
# Kayıp Fonksiyonları
# ---------------------------------------------------------------------------

class _GIoULoss(nn.Module):
    """GIoU kaybı — FCOS box regression için."""

    def forward(
        self,
        pred: torch.Tensor,  # (N, 4) ltrb
        tgt: torch.Tensor,   # (N, 4) ltrb
    ) -> torch.Tensor:
        pred_area = (pred[:, 0] + pred[:, 2]) * (pred[:, 1] + pred[:, 3])
        tgt_area  = (tgt[:, 0] + tgt[:, 2]) * (tgt[:, 1] + tgt[:, 3])

        inter_w = (torch.minimum(pred[:, 0], tgt[:, 0]) + torch.minimum(pred[:, 2], tgt[:, 2])).clamp(0)
        inter_h = (torch.minimum(pred[:, 1], tgt[:, 1]) + torch.minimum(pred[:, 3], tgt[:, 3])).clamp(0)
        inter   = inter_w * inter_h
        union   = pred_area + tgt_area - inter
        iou     = inter / (union + 1e-6)

        enc_w = torch.maximum(pred[:, 0], tgt[:, 0]) + torch.maximum(pred[:, 2], tgt[:, 2])
        enc_h = torch.maximum(pred[:, 1], tgt[:, 1]) + torch.maximum(pred[:, 3], tgt[:, 3])
        enc_area = enc_w * enc_h
        giou = iou - (enc_area - union) / (enc_area + 1e-6)
        return (1 - giou).mean()


class OBTLoss(nn.Module):
    """
    Birleşik OBT kaybı:
      L = λ_patient * L_patient + λ_slice * L_slice
        + λ_cls * L_det_cls + λ_box * L_det_box + λ_ctr * L_centerness
    """

    def __init__(
        self,
        lambda_patient: float = 1.0,
        lambda_slice: float = 0.5,
        lambda_det_cls: float = 0.3,
        lambda_det_box: float = 0.3,
        lambda_centerness: float = 0.1,
        focal_gamma: float = 2.0,
        class_weights: Optional[torch.Tensor] = None,
    ):
        super().__init__()
        self.lam = dict(
            patient=lambda_patient,
            slice=lambda_slice,
            det_cls=lambda_det_cls,
            det_box=lambda_det_box,
            centerness=lambda_centerness,
        )
        self.gamma = focal_gamma
        self.register_buffer(
            "class_weights",
            class_weights if class_weights is not None else torch.ones(N_CLASSES),
        )
        self.giou = _GIoULoss()

    def _focal_bce(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits, targets, reduction="none")
        pt = torch.exp(-bce)
        focal = (1 - pt) ** self.gamma * bce
        focal = focal * self.class_weights.to(logits.device)
        return focal.mean()

    def forward(
        self,
        patient_logits: torch.Tensor,               # (6,)
        patient_labels: torch.Tensor,               # (6,)
        slice_logits: Optional[torch.Tensor] = None,  # (B, 6, H, W) → pool'lanacak
        slice_labels: Optional[torch.Tensor] = None,  # (B, 6)
        fcos_cls: Optional[torch.Tensor] = None,
        fcos_box: Optional[torch.Tensor] = None,
        fcos_ctr: Optional[torch.Tensor] = None,
        box_targets: Optional[Dict] = None,
    ) -> Tuple[torch.Tensor, Dict[str, float]]:
        """
        box_targets keys: "cls_map" (B,6,H,W), "box_map" (B,4,H,W),
                          "pos_mask" (B,H,W), "centerness_map" (B,1,H,W)
        """
        log: Dict[str, float] = {}
        total = torch.zeros(1, device=patient_logits.device, requires_grad=True)

        # Hasta-düzeyi
        lp = self._focal_bce(patient_logits.unsqueeze(0), patient_labels.float().unsqueeze(0))
        log["patient"] = lp.item()
        total = total + self.lam["patient"] * lp

        # Dilim-düzeyi
        if slice_logits is not None and slice_labels is not None:
            slice_pred = slice_logits.mean(dim=(-2, -1))   # (B, 6)
            ls = self._focal_bce(slice_pred, slice_labels.float())
            log["slice"] = ls.item()
            total = total + self.lam["slice"] * ls

        # FCOS
        if fcos_cls is not None and box_targets is not None:
            cls_tgt = box_targets.get("cls_map")
            if cls_tgt is not None:
                lc = self._focal_bce(fcos_cls, cls_tgt.float())
                log["det_cls"] = lc.item()
                total = total + self.lam["det_cls"] * lc

            box_tgt = box_targets.get("box_map")
            pos_mask = box_targets.get("pos_mask")
            if fcos_box is not None and box_tgt is not None and pos_mask is not None:
                pos_mask_flat = pos_mask.reshape(-1).bool()
                if pos_mask_flat.any():
                    pred_flat = fcos_box.permute(0, 2, 3, 1).reshape(-1, 4)[pos_mask_flat]
                    tgt_flat  = box_tgt.permute(0, 2, 3, 1).reshape(-1, 4)[pos_mask_flat]
                    lb = self.giou(pred_flat, tgt_flat)
                    log["det_box"] = lb.item()
                    total = total + self.lam["det_box"] * lb

            if fcos_ctr is not None:
                ctr_tgt = box_targets.get("centerness_map")
                if ctr_tgt is not None:
                    lctr = F.binary_cross_entropy_with_logits(fcos_ctr, ctr_tgt.float())
                    log["centerness"] = lctr.item()
                    total = total + self.lam["centerness"] * lctr

        return total.squeeze(), log


# ---------------------------------------------------------------------------
# FCOS Çıktı Dekodlayıcı
# ---------------------------------------------------------------------------

@torch.no_grad()
def decode_fcos_output(
    cls_logits: torch.Tensor,   # (1, 6, H, W)
    reg_ltrb: torch.Tensor,     # (1, 4, H, W)
    centerness: torch.Tensor,   # (1, 1, H, W)
    stride: int = 32,
    score_thr: float = 0.05,
    nms_iou_thr: float = 0.5,
) -> List[Dict]:
    """
    FCOS çıktısını bounding-box listesine dönüştürür.
    Basit NMS uygulanmaz (downstream evaluation için ham kutuları döner).

    Döndürür: [{"box": [x1,y1,x2,y2], "score": float, "class": int}]
    """
    H, W = cls_logits.shape[-2:]
    device = cls_logits.device

    ys, xs = torch.meshgrid(
        torch.arange(H, device=device) * stride + stride // 2,
        torch.arange(W, device=device) * stride + stride // 2,
        indexing="ij",
    )

    scores = cls_logits[0].sigmoid() * centerness[0, 0].sigmoid().unsqueeze(0)  # (6,H,W)
    ltrb   = reg_ltrb[0]  # (4, H, W)

    detections = []
    for c in range(N_CLASSES):
        mask = scores[c] > score_thr
        if not mask.any():
            continue
        cx, cy = xs[mask], ys[mask]
        l, t, r, b = ltrb[0][mask], ltrb[1][mask], ltrb[2][mask], ltrb[3][mask]
        for i in range(mask.sum()):
            detections.append({
                "box": [
                    (cx[i] - l[i]).item(), (cy[i] - t[i]).item(),
                    (cx[i] + r[i]).item(), (cy[i] + b[i]).item(),
                ],
                "score": scores[c][mask][i].item(),
                "class": c,
            })

    return detections


# ---------------------------------------------------------------------------
# Türetilmiş Çıktılar (eğitim gerekmez)
# ---------------------------------------------------------------------------

@torch.no_grad()
def compute_triage_score(patient_probs: torch.Tensor) -> Tuple[float, str]:
    """Hasta-düzeyi triyaj skoru (türetilmiş)."""
    score = patient_probs.max().item()
    label = "acil" if score > 0.7 else ("gözlem" if score > 0.3 else "normal")
    return score, label


@torch.no_grad()
def compute_uncertainty(patient_logits: torch.Tensor) -> float:
    """Shannon entropi üzerinden belirsizlik skoru ∈ [0, 1]."""
    p = patient_logits.sigmoid().clamp(1e-6, 1 - 1e-6)
    h = -(p * p.log() + (1 - p) * (1 - p).log())
    return (h.mean() / np.log(2)).item()
