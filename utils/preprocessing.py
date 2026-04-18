"""
CarbonKarma — Satellite data preprocessing.

Responsibilities:
  - Lee filter for SAR speckle reduction
  - CRS alignment (simulated — normalise patches to a common spatial grid)
  - NDVI calculation from band arrays
  - Land-surface temperature normalisation
  - Soil moisture proxy from SAR + NDVI

All functions operate on NumPy arrays (float32, shape H×W).
"""

from __future__ import annotations

import numpy as np
import cv2


# ---------------------------------------------------------------------------
# SAR preprocessing
# ---------------------------------------------------------------------------

def lee_filter(
    image: np.ndarray,
    window_size: int = 5,
    noise_var: float = 0.25,
) -> np.ndarray:
    """
    Simulated Lee speckle filter for SAR backscatter.

    The Lee filter weights local mean and variance to suppress multiplicative
    speckle noise while preserving edge features.

    Parameters
    ----------
    image       : 2-D float32 array (single polarisation band).
    window_size : Size of the local neighbourhood (must be odd).
    noise_var   : Assumed noise variance (σ²_n). Typical SAR ≈ 0.25.

    Returns filtered image (same shape, float32).
    """
    if window_size % 2 == 0:
        window_size += 1

    img = image.astype(np.float32)
    kernel = np.ones((window_size, window_size), dtype=np.float32) / (window_size ** 2)

    # Local mean and local variance
    local_mean = cv2.filter2D(img, -1, kernel, borderType=cv2.BORDER_REFLECT)
    local_sq_mean = cv2.filter2D(img ** 2, -1, kernel, borderType=cv2.BORDER_REFLECT)
    local_var = local_sq_mean - local_mean ** 2
    local_var = np.maximum(local_var, 0.0)

    # Lee weighting coefficient
    img_var = np.var(img) + 1e-9
    weight = local_var / (local_var + noise_var * img_var)

    filtered = local_mean + weight * (img - local_mean)
    return filtered.astype(np.float32)


# ---------------------------------------------------------------------------
# CRS alignment 
# ---------------------------------------------------------------------------

def align_to_common_grid(
    patches: dict[str, np.ndarray],
    target_size: int,
) -> dict[str, np.ndarray]:
    """
    Resample all input patches to a common (target_size × target_size) grid.

    In production this would perform proper CRS reprojection (e.g. via GDAL /
    rasterio). Here we simulate it with bilinear interpolation so that every
    band occupies the same pixel grid before fusion.

    Parameters
    ----------
    patches     : Dict of band-name → 2-D array (any size).
    target_size : Desired output size in pixels.

    Returns a dict with the same keys, all resized to (target_size, target_size).
    """
    aligned: dict[str, np.ndarray] = {}
    for name, arr in patches.items():
        if arr.shape == (target_size, target_size):
            aligned[name] = arr.astype(np.float32)
        else:
            resized = cv2.resize(
                arr.astype(np.float32),
                (target_size, target_size),
                interpolation=cv2.INTER_LINEAR,
            )
            aligned[name] = resized
    return aligned


# ---------------------------------------------------------------------------
# NDVI
# ---------------------------------------------------------------------------

def compute_ndvi(
    red_band: np.ndarray,
    nir_band: np.ndarray,
) -> np.ndarray:
    """
    Normalised Difference Vegetation Index.

        NDVI = (NIR − RED) / (NIR + RED)

    Result is clipped to [−1, 1]. Areas with zero denominator return 0.
    """
    red = red_band.astype(np.float32)
    nir = nir_band.astype(np.float32)
    denom = nir + red
    ndvi = np.where(np.abs(denom) > 1e-6, (nir - red) / denom, 0.0)
    return np.clip(ndvi, -1.0, 1.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Land Surface Temperature normalisation
# ---------------------------------------------------------------------------

def normalise_temperature(
    lst_array: np.ndarray,
    t_min_kelvin: float = 270.0,
    t_max_kelvin: float = 330.0,
) -> np.ndarray:
    """
    Normalise a Land Surface Temperature patch (Kelvin) to [0, 1].

    Default range covers −3 °C → 57 °C — adequate for tropical rice fields.
    """
    arr = np.clip(lst_array.astype(np.float32), t_min_kelvin, t_max_kelvin)
    return (arr - t_min_kelvin) / (t_max_kelvin - t_min_kelvin)


# ---------------------------------------------------------------------------
# Soil moisture proxy
# ---------------------------------------------------------------------------

def estimate_soil_moisture(
    vv_band: np.ndarray,
    vh_band: np.ndarray,
    ndvi: np.ndarray,
) -> np.ndarray:
    """
    Physics-informed soil moisture proxy combining SAR cross-polarisation
    ratio and NDVI-based vegetation correction.

    Formula (empirical):
        SM_proxy = σ(α · VH/VV · (1 − NDVI·β))

    where σ is sigmoid and α, β are empirical scale factors.

    Returns a (H × W) float32 array in [0, 1].
    """
    alpha: float = 3.0
    beta: float = 0.5

    vv = np.maximum(vv_band.astype(np.float32), 1e-9)
    vh = vh_band.astype(np.float32)
    ndvi_clipped = np.clip(ndvi, -1.0, 1.0)

    ratio = vh / vv
    vegetation_correction = 1.0 - ndvi_clipped * beta
    raw = alpha * ratio * vegetation_correction

    # Sigmoid activation → [0, 1]
    soil_moisture = 1.0 / (1.0 + np.exp(-raw))
    return soil_moisture.astype(np.float32)


# ---------------------------------------------------------------------------
# Water probability from SAR
# ---------------------------------------------------------------------------

def compute_water_probability(
    vv_band: np.ndarray,
    vh_band: np.ndarray,
    vv_water_thresh: float = -0.45,
    vh_water_thresh: float = -0.55,
) -> np.ndarray:
    """
    Estimate per-pixel water probability from SAR backscatter.

    Water surfaces produce very low backscatter (specular reflection).
    We score each pixel using a soft Gaussian distance from known water
    backscatter signatures in both VV and VH channels.

    Returns (H × W) float32 in [0, 1].
    """
    vv = vv_band.astype(np.float32)
    vh = vh_band.astype(np.float32)

    sigma = 0.15
    prob_vv = np.exp(-((vv - vv_water_thresh) ** 2) / (2 * sigma ** 2))
    prob_vh = np.exp(-((vh - vh_water_thresh) ** 2) / (2 * sigma ** 2))

    # Combine channels with equal weight, add noise to simulate real sensor
    prob = (prob_vv * 0.6 + prob_vh * 0.4)
    noise = np.random.normal(0, 0.02, prob.shape).astype(np.float32)
    prob = np.clip(prob + noise, 0.0, 1.0)
    return prob
