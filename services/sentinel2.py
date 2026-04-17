"""
CarbonKarma — Sentinel-2 MSI data ingestion service.

Simulates Sentinel-2 Level-2A (surface reflectance) bands over a paddy rice
field at multiple time steps. In production this calls the Sentinel Hub
EvalScript API or a STAC catalogue (e.g. AWS OpenData).

Bands simulated:
  B02 (Blue, 490 nm), B03 (Green, 560 nm), B04 (Red, 665 nm),
  B08 (NIR, 842 nm) — all at 10 m native resolution.

Physics notes:
  - Young flooded paddy: high Blue, low NIR → NDVI ~ -0.1 to 0.1
  - Vegetating paddy (tillering/heading): NDVI rises to 0.6-0.8
  - Ripening / senescence: NDVI drops back to 0.3-0.5
  - Cloud contamination simulated with random probability
"""

from __future__ import annotations

import cv2
import numpy as np
from typing import Any, Dict, List, Optional

from config import config
from utils.preprocessing import compute_ndvi


# ---------------------------------------------------------------------------
# Reflectance tables per phenology stage
# ---------------------------------------------------------------------------

# (blue, green, red, nir) mean surface reflectance, flooded vs vegetated
_REFLECTANCE = {
    #  stage          : (blue_f, green_f, red_f, nir_f,  blue_d, green_d, red_d, nir_d)
    "transplanting":   (0.08, 0.10, 0.07, 0.09,  0.04, 0.07, 0.05, 0.15),
    "tillering":       (0.05, 0.09, 0.06, 0.30,  0.04, 0.08, 0.05, 0.45),
    "heading":         (0.04, 0.08, 0.05, 0.50,  0.04, 0.07, 0.05, 0.60),
    "ripening":        (0.05, 0.09, 0.07, 0.40,  0.05, 0.10, 0.08, 0.35),
    "harvest":         (0.07, 0.11, 0.09, 0.20,  0.08, 0.12, 0.10, 0.18),
}


def _simulate_band_patch(
    patch_size: int,
    mean_reflectance: float,
    std: float = 0.015,
) -> np.ndarray:
    """Generate a spatially smooth reflectance patch (H × W)."""
    base = np.random.normal(mean_reflectance, std, (patch_size, patch_size)).astype(np.float32)
    kernel = max(3, patch_size // 6)
    if kernel % 2 == 0:
        kernel += 1
    base = cv2.GaussianBlur(base, (kernel, kernel), 0)
    return np.clip(base, 0.0, 1.0).astype(np.float32)


def _apply_cloud_mask(
    band: np.ndarray,
    cloud_prob: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Randomly mask pixels with simulated cloud cover.

    Returns (masked_band, cloud_mask) where cloud_mask is True where cloudy.
    """
    mask = np.random.random(band.shape) < cloud_prob
    masked = band.copy()
    masked[mask] = 1.0   # Clouds appear bright in all bands
    return masked.astype(np.float32), mask


def _true_color_composite(
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
) -> np.ndarray:
    """
    Stack R/G/B into a (H × W × 3) uint8 array with histogram stretch.
    Returns an image suitable for JPEG/PNG encoding or base64 export.
    """
    def stretch(band: np.ndarray) -> np.ndarray:
        p2, p98 = np.percentile(band, (2, 98))
        stretched = (band - p2) / max(p98 - p2, 1e-6)
        return np.clip(stretched * 255, 0, 255).astype(np.uint8)

    rgb = np.stack([stretch(red), stretch(green), stretch(blue)], axis=-1)
    return rgb


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_sentinel2(
    lat: float,
    lon: float,
    timestamps: List[str],
    patch_size: Optional[int] = None,
    awd_pattern: Optional[List[bool]] = None,
    cloud_probability: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Return a list of Sentinel-2 observations, one per timestamp.

    Parameters
    ----------
    lat, lon          : Field centroid.
    timestamps        : Ordered list of ISO date strings.
    patch_size        : Spatial patch size in pixels.
    awd_pattern       : Optional list of bool (True=flooded) per timestamp.
    cloud_probability : Per-pixel cloud contamination probability [0, 1].

    Each returned record contains:
        timestamp      : ISO string
        blue, green, red, nir : (H×W) float32 surface reflectance patches
        ndvi_map       : (H×W) per-pixel NDVI
        ndvi_mean      : scalar mean NDVI (cloud-free pixels only)
        ndvi_std       : scalar std NDVI
        true_color     : (H×W×3) uint8 RGB composite
        cloud_mask     : (H×W) bool — True where cloudy
        cloud_fraction : fraction of pixels masked
        phenology_stage: string
        is_flooded     : bool
    """
    patch_size = patch_size or config.PATCH_SIZE

    # Mirror sentinel1 phenology helper
    def _stage(day: int) -> str:
        if day < 16:   return "transplanting"
        elif day < 41: return "tillering"
        elif day < 66: return "heading"
        elif day < 91: return "ripening"
        else:          return "harvest"

    if awd_pattern is None:
        awd_pattern = [i % 12 < 7 for i in range(len(timestamps))]

    records: List[Dict[str, Any]] = []

    for idx, ts in enumerate(timestamps):
        is_flooded = awd_pattern[idx % len(awd_pattern)]
        stage = _stage(idx * 10)
        row = _REFLECTANCE.get(stage, (0.05, 0.08, 0.06, 0.25,  0.05, 0.09, 0.07, 0.30))

        if is_flooded:
            b_m, g_m, r_m, n_m = row[0], row[1], row[2], row[3]
        else:
            b_m, g_m, r_m, n_m = row[4], row[5], row[6], row[7]

        # Add inter-scene variability
        jitter = np.random.normal(0, 0.005, 4)
        b_m = max(0.01, b_m + jitter[0])
        g_m = max(0.01, g_m + jitter[1])
        r_m = max(0.01, r_m + jitter[2])
        n_m = max(0.01, n_m + jitter[3])

        blue  = _simulate_band_patch(patch_size, b_m)
        green = _simulate_band_patch(patch_size, g_m)
        red   = _simulate_band_patch(patch_size, r_m)
        nir   = _simulate_band_patch(patch_size, n_m)

        # Cloud masking
        red_c, cloud_mask = _apply_cloud_mask(red, cloud_probability)
        nir_c, _         = _apply_cloud_mask(nir, cloud_probability)

        ndvi_map = compute_ndvi(red_c, nir_c)
        cloud_fraction = float(cloud_mask.mean())

        # Compute mean NDVI only on clear pixels
        clear_ndvi = ndvi_map[~cloud_mask]
        ndvi_mean = float(clear_ndvi.mean()) if clear_ndvi.size > 0 else float(ndvi_map.mean())
        ndvi_std  = float(clear_ndvi.std())  if clear_ndvi.size > 0 else float(ndvi_map.std())

        true_color = _true_color_composite(red_c, green, blue)

        records.append({
            "timestamp": ts,
            "blue": blue,
            "green": green,
            "red": red_c,
            "nir": nir_c,
            "ndvi_map": ndvi_map,
            "ndvi_mean": round(ndvi_mean, 4),
            "ndvi_std": round(ndvi_std, 4),
            "true_color": true_color,
            "cloud_mask": cloud_mask,
            "cloud_fraction": round(cloud_fraction, 4),
            "phenology_stage": stage,
            "is_flooded": bool(is_flooded),
        })

    return records
