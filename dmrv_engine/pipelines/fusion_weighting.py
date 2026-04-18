"""
Solves the "information redundancy" problem between Sentinel-1 SAR and
Sentinel-2 optical data.

PROBLEM
-------
Both sensors theoretically detect water. When they agree, we have redundant
but confirming evidence. When they disagree, we need a principled way to
decide which to trust.

KEY SCIENTIFIC INSIGHT
----------------------
At EVI > ~0.80, the rice canopy is so dense that optical sensors can no
longer "see" the water underneath it. NDWI becomes unreliable in this regime,
and our trust must shift almost entirely to SAR, which can penetrate canopy.

Conversely, over bare or sparsely-vegetated fields (EVI < 0.3), the SAR
VH/VV ratio is more ambiguous (any smooth surface reflects specularly).
In this regime we should trust optical NDWI more.

Regional variability: VH/VV sensitivity depends on soil moisture, roughness,
and incidence angle. `region_profile` lets callers inject regional priors
derived from historical calibration.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, Union

import numpy as np

try:
    import torch
    _TORCH_AVAILABLE = True
    ArrayLike = Union[torch.Tensor, np.ndarray]
except ImportError:
    _TORCH_AVAILABLE = False
    ArrayLike = np.ndarray  # type: ignore

from config.settings import get_settings

logger = logging.getLogger(__name__)


# ── Regional calibration profiles ──────────────────────────────────────
# These are defensible starting priors; in production they come from
# regional SAR backscatter histograms against ground-truth flood masks.

REGION_PROFILES: dict[str, dict] = {
    "south_asia":       {"sar_sensitivity": 1.00, "evi_saturation": 0.78, "vh_vv_water_db": -22.0},
    "southeast_asia":   {"sar_sensitivity": 0.95, "evi_saturation": 0.82, "vh_vv_water_db": -21.0},
    "east_asia":        {"sar_sensitivity": 0.90, "evi_saturation": 0.80, "vh_vv_water_db": -22.5},
    "sub_saharan":      {"sar_sensitivity": 0.85, "evi_saturation": 0.75, "vh_vv_water_db": -20.5},
    "default":          {"sar_sensitivity": 1.00, "evi_saturation": 0.80, "vh_vv_water_db": -22.0},
}


# ── Data transfer objects ──────────────────────────────────────────────

@dataclass
class FusionWeights:
    """Per-pixel fusion weights and metadata."""
    sar_weight:         ArrayLike   # weight applied to SAR water prediction
    optical_weight:     ArrayLike   # weight applied to optical water prediction (NDWI)
    saturation_mask:    ArrayLike   # bool mask where EVI > saturation threshold
    saturation_pct:     float       # fraction of pixels in saturation regime
    mode:               str         # "optical_dominant" | "sar_dominant" | "balanced"
    region:             str
    evi_threshold:      float
    sar_sensitivity:    float


@dataclass
class WaterProbability:
    """Final fused water probability map."""
    water_prob:         ArrayLike   # [0, 1] per pixel
    weights:            FusionWeights
    sar_component:      ArrayLike   # SAR-derived water prob
    optical_component:  ArrayLike   # NDWI-derived water prob
    agreement_pct:      float       # fraction of pixels where SAR and optical agree


# ── Helpers ────────────────────────────────────────────────────────────

def _is_torch(x: ArrayLike) -> bool:
    return _TORCH_AVAILABLE and isinstance(x, torch.Tensor)

def _sigmoid(x: ArrayLike) -> ArrayLike:
    if _is_torch(x):
        return torch.sigmoid(x)
    return 1.0 / (1.0 + np.exp(-np.clip(x, -50, 50)))

def _ones_like(x: ArrayLike) -> ArrayLike:
    return torch.ones_like(x) if _is_torch(x) else np.ones_like(x)

def _zeros_like(x: ArrayLike) -> ArrayLike:
    return torch.zeros_like(x) if _is_torch(x) else np.zeros_like(x)

def _where(cond, a, b):
    return torch.where(cond, a, b) if _is_torch(cond) else np.where(cond, a, b)

def _mean(x: ArrayLike) -> float:
    return float(x.mean().item() if _is_torch(x) else np.mean(x))


# ── Core fusion logic ──────────────────────────────────────────────────

def compute_fusion_weights(
    evi: ArrayLike,
    region: str = "default",
    settings_override: Optional[dict] = None,
) -> FusionWeights:
    """
    Compute per-pixel fusion weights based on EVI saturation.

    Weighting scheme (smooth, not hard-gated):
        EVI=0.0 → optical=1.0, sar=0.5   (sparse canopy: trust optical more)
        EVI=0.5 → optical=0.7, sar=0.7   (moderate canopy: balanced)
        EVI=0.8 → optical=0.3, sar=1.0   (dense canopy: trust SAR)
        EVI=1.0 → optical=0.0, sar=1.0   (saturated: SAR only)

    Uses a smooth logistic transition centered at the saturation threshold.

    Args:
        evi: Per-pixel EVI array of shape (..., H, W).
        region: Regional calibration profile key (see REGION_PROFILES).
        settings_override: Optional dict to override region profile values.

    Returns:
        FusionWeights with per-pixel sar/optical weights.
    """
    profile = {**REGION_PROFILES.get(region, REGION_PROFILES["default"])}
    if settings_override:
        profile.update(settings_override)

    evi_threshold   = profile["evi_saturation"]
    sar_sensitivity = profile["sar_sensitivity"]

    # Smooth logistic transition around EVI threshold
    # Steepness=20 gives ~95% transition within ±0.1 of threshold
    saturation_score = _sigmoid((evi - evi_threshold) * 20.0)

    # Optical weight decays as saturation rises
    optical_weight = (1.0 - saturation_score) * 1.0 + 0.0
    # SAR weight grows as saturation rises, modulated by regional sensitivity
    sar_weight = (0.5 + saturation_score * 0.5) * sar_sensitivity

    # Hard mask for reporting / downstream use
    saturation_mask = evi > evi_threshold
    saturation_pct  = _mean(saturation_mask.float() if _is_torch(saturation_mask)
                            else saturation_mask.astype(np.float32))

    mode = (
        "sar_dominant"     if saturation_pct > 0.6 else
        "optical_dominant" if saturation_pct < 0.2 else
        "balanced"
    )

    return FusionWeights(
        sar_weight=sar_weight,
        optical_weight=optical_weight,
        saturation_mask=saturation_mask,
        saturation_pct=saturation_pct,
        mode=mode,
        region=region,
        evi_threshold=evi_threshold,
        sar_sensitivity=sar_sensitivity,
    )


def sar_water_probability(
    vv_db:   ArrayLike,
    vh_db:   ArrayLike,
    region:  str = "default",
) -> ArrayLike:
    """
    Compute water probability from SAR backscatter.

    Water surfaces appear very dark in SAR (specular reflection) — both VV and
    VH drop, and VH/VV ratio becomes distinctive (<-22 dB typical for water).

    Uses a logistic transition around the region-specific VH/VV threshold.
    """
    profile = REGION_PROFILES.get(region, REGION_PROFILES["default"])
    threshold_db = profile["vh_vv_water_db"]

    # VH - VV in dB space is equivalent to log(VH/VV)
    vh_vv_ratio_db = vh_db - vv_db

    # Pixels below threshold → high water prob
    # Steepness=0.5 gives a ~4 dB transition zone
    water_prob = _sigmoid(-(vh_vv_ratio_db - threshold_db) * 0.5)
    return water_prob


def optical_water_probability(
    ndwi: ArrayLike,
    threshold: Optional[float] = None,
) -> ArrayLike:
    """Convert NDWI to water probability via logistic around threshold."""
    thr = threshold if threshold is not None else get_settings().NDWI_WATER_THRESHOLD
    return _sigmoid((ndwi - thr) * 10.0)


def fuse_water_detection(
    vv_db:  ArrayLike,
    vh_db:  ArrayLike,
    ndwi:   ArrayLike,
    evi:    ArrayLike,
    region: str = "default",
) -> WaterProbability:
    """
    High-level fusion: compute weighted water probability.

    This is the main entry point for upstream callers. Combines:
      1. SAR water detection (VV, VH backscatter)
      2. Optical water detection (NDWI)
      3. EVI-gated weighting (resolve redundancy)

    Returns:
        WaterProbability with fused map, weights, and component arrays.
    """
    sar_p     = sar_water_probability(vv_db, vh_db, region=region)
    optical_p = optical_water_probability(ndwi)

    weights = compute_fusion_weights(evi, region=region)

    # Normalise weights so they sum to 1 per pixel
    total_w = weights.sar_weight + weights.optical_weight + 1e-8
    fused = (weights.sar_weight * sar_p + weights.optical_weight * optical_p) / total_w

    # Agreement metric: where both sensors predict the same class (both >0.5 or both <0.5)
    sar_class  = sar_p > 0.5
    opt_class  = optical_p > 0.5
    agreement  = sar_class == opt_class
    agree_pct  = _mean(agreement.float() if _is_torch(agreement)
                       else agreement.astype(np.float32))

    return WaterProbability(
        water_prob=fused,
        weights=weights,
        sar_component=sar_p,
        optical_component=optical_p,
        agreement_pct=agree_pct,
    )
