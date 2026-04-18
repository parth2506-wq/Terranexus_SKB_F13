"""
Optical vegetation and water indices computed from Sentinel-2 surface
reflectance tensors.

Formulas are based on Huete et al. (2002) and McFeeters (1996).
All functions accept tensors of shape (..., H, W) with floating-point
reflectance values in [0, 1]. Works with both PyTorch and NumPy arrays.
"""
from __future__ import annotations

import logging
from typing import Union

import numpy as np

try:
    import torch
    _TORCH_AVAILABLE = True
    ArrayLike = Union[torch.Tensor, np.ndarray]
except ImportError:
    _TORCH_AVAILABLE = False
    ArrayLike = np.ndarray  # type: ignore

logger = logging.getLogger(__name__)


# ── EVI coefficients (Huete et al., 2002, MODIS ATBD) ───────────────────
EVI_G  = 2.5    # gain
EVI_C1 = 6.0    # aerosol resistance coefficient (red)
EVI_C2 = 7.5    # aerosol resistance coefficient (blue)
EVI_L  = 1.0    # canopy background adjustment

_EPS = 1e-8


# ── Internal helpers ────────────────────────────────────────────────────

def _is_torch(x: ArrayLike) -> bool:
    return _TORCH_AVAILABLE and isinstance(x, torch.Tensor)

def _clamp(x: ArrayLike, lo: float, hi: float) -> ArrayLike:
    if _is_torch(x):
        return torch.clamp(x, lo, hi)
    return np.clip(x, lo, hi)


# ── Public: index computation ───────────────────────────────────────────

def compute_evi(
    nir:  ArrayLike,
    red:  ArrayLike,
    blue: ArrayLike,
    clamp_range: tuple[float, float] = (-1.0, 1.0),
) -> ArrayLike:
    """
    Enhanced Vegetation Index (Huete et al., 2002).

        EVI = G * (NIR - RED) / (NIR + C1*RED - C2*BLUE + L)

    EVI improves sensitivity over dense canopies (NDVI saturates around
    LAI=3; EVI remains sensitive up to LAI=5-6), critical for heading-stage
    rice paddies. Uses the Blue band for atmospheric resistance.

    Args:
        nir:   Sentinel-2 B8 (842 nm) surface reflectance, in [0, 1].
        red:   Sentinel-2 B4 (665 nm) surface reflectance, in [0, 1].
        blue:  Sentinel-2 B2 (490 nm) surface reflectance, in [0, 1].
        clamp_range: (lo, hi) to clip results.

    Returns:
        EVI tensor of same shape as inputs, typically in [-1, 1].
    """
    _validate_shapes(nir, red, blue)

    numerator   = nir - red
    denominator = nir + EVI_C1 * red - EVI_C2 * blue + EVI_L + _EPS
    evi = EVI_G * (numerator / denominator)

    return _clamp(evi, *clamp_range)


def compute_ndwi(
    green: ArrayLike,
    nir:   ArrayLike,
    clamp_range: tuple[float, float] = (-1.0, 1.0),
) -> ArrayLike:
    """
    Normalized Difference Water Index (McFeeters, 1996).

        NDWI = (GREEN - NIR) / (GREEN + NIR)

    NDWI > ~0.3 typically indicates surface water. Used as an independent
    optical confirmation of SAR-based flood detection (sanity check).

    Args:
        green: Sentinel-2 B3 (560 nm) surface reflectance, in [0, 1].
        nir:   Sentinel-2 B8 (842 nm) surface reflectance, in [0, 1].

    Returns:
        NDWI tensor of same shape as inputs, in [-1, 1].
    """
    _validate_shapes(green, nir)
    ndwi = (green - nir) / (green + nir + _EPS)
    return _clamp(ndwi, *clamp_range)


def compute_ndvi(
    nir: ArrayLike,
    red: ArrayLike,
    clamp_range: tuple[float, float] = (-1.0, 1.0),
) -> ArrayLike:
    """
    Normalized Difference Vegetation Index (classic, Rouse et al. 1974).

    Kept for backwards compatibility; EVI is preferred for dense canopies.
    """
    _validate_shapes(nir, red)
    ndvi = (nir - red) / (nir + red + _EPS)
    return _clamp(ndvi, *clamp_range)


# ── Batch / convenience API ─────────────────────────────────────────────

def compute_all_indices(sentinel2_bands: dict) -> dict:
    """
    Compute EVI, NDVI, NDWI from a dict of Sentinel-2 reflectance bands.

    Args:
        sentinel2_bands: dict with keys at least {'B2', 'B3', 'B4', 'B8'}
                         and tensor values of matching shape.

    Returns:
        dict of {'evi': ..., 'ndvi': ..., 'ndwi': ...}

    Raises:
        KeyError if a required band is missing.
    """
    required = {"B2", "B3", "B4", "B8"}
    missing = required - set(sentinel2_bands.keys())
    if missing:
        raise KeyError(f"Missing required Sentinel-2 bands: {sorted(missing)}")

    blue  = sentinel2_bands["B2"]
    green = sentinel2_bands["B3"]
    red   = sentinel2_bands["B4"]
    nir   = sentinel2_bands["B8"]

    return {
        "evi":  compute_evi (nir=nir, red=red, blue=blue),
        "ndvi": compute_ndvi(nir=nir, red=red),
        "ndwi": compute_ndwi(green=green, nir=nir),
    }


# ── Validation ──────────────────────────────────────────────────────────

def _validate_shapes(*arrays: ArrayLike) -> None:
    if not arrays:
        return
    shapes = [tuple(a.shape) for a in arrays]
    if len(set(shapes)) > 1:
        raise ValueError(f"All bands must have identical shape. Got: {shapes}")
