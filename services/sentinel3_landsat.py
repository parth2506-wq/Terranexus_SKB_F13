"""
CarbonKarma — Sentinel-3 SLSTR / Landsat LST ingestion service.

Simulates Land Surface Temperature (LST) and Top-of-Atmosphere brightness
temperature fields over a paddy rice area at multiple time steps.

In production:
  - Sentinel-3 SLSTR L2 LST product (1 km resolution): Copernicus Open Access Hub
  - Landsat Collection-2 ST product (30 m resolution): USGS EarthExplorer / AWS

Simulation physics:
  - Rice field LST follows diurnal and seasonal cycles
  - Flooded periods are ~2-5 °C cooler than dry periods (evaporative cooling)
  - Ambient air temperature from Open-Meteo drives the baseline
  - Spatial variation simulates field-scale heterogeneity

Outputs:
  - lst_raw     : Kelvin (H×W)
  - lst_celsius : Celsius scalar mean
  - lst_norm    : [0,1] normalised (H×W) for model input
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import cv2
import numpy as np

from config import config
from utils.preprocessing import normalise_temperature


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ambient_temp_kelvin(
    timestamp: str,
    base_celsius: float = 30.0,
) -> float:
    """
    Estimate ambient temperature in Kelvin from the timestamp month and a base.
    Applies a simple sinusoidal seasonal correction (Northern Hemisphere).
    """
    from datetime import date
    d = date.fromisoformat(timestamp)
    # Month 1 (Jan) = cold, Month 7 (Jul) = hot (N. Hemisphere paddy season)
    seasonal_offset = 5.0 * np.sin(2 * np.pi * (d.month - 3) / 12)
    ambient_c = base_celsius + seasonal_offset
    return ambient_c + 273.15


def _simulate_lst_patch(
    patch_size: int,
    mean_kelvin: float,
    std_kelvin: float = 1.5,
) -> np.ndarray:
    """Generate a spatially smooth LST patch in Kelvin (H×W)."""
    base = np.random.normal(mean_kelvin, std_kelvin, (patch_size, patch_size)).astype(np.float32)
    kernel = max(3, patch_size // 5)
    if kernel % 2 == 0:
        kernel += 1
    return cv2.GaussianBlur(base, (kernel, kernel), 0).astype(np.float32)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_lst(
    lat: float,
    lon: float,
    timestamps: List[str],
    patch_size: Optional[int] = None,
    awd_pattern: Optional[List[bool]] = None,
    base_celsius: float = 30.0,
) -> List[Dict[str, Any]]:
    """
    Return a list of LST observations, one per timestamp.

    Each record:
        timestamp       : ISO string
        lst_raw         : (H×W) float32 LST patch in Kelvin
        lst_celsius_map : (H×W) float32 in Celsius
        lst_norm        : (H×W) float32 normalised [0,1]
        lst_mean_kelvin : scalar mean
        lst_mean_celsius: scalar mean in °C
        lst_std         : scalar std in Kelvin
        is_flooded      : bool
    """
    patch_size = patch_size or config.PATCH_SIZE

    if awd_pattern is None:
        awd_pattern = [i % 12 < 7 for i in range(len(timestamps))]

    records: List[Dict[str, Any]] = []

    for idx, ts in enumerate(timestamps):
        is_flooded = awd_pattern[idx % len(awd_pattern)]
        ambient_k = _ambient_temp_kelvin(ts, base_celsius)

        # Flooded fields are cooler due to evapotranspiration
        if is_flooded:
            mean_k = ambient_k - np.random.uniform(2.0, 5.0)
        else:
            mean_k = ambient_k + np.random.uniform(0.5, 3.0)

        lst_raw = _simulate_lst_patch(patch_size, mean_k, std_kelvin=1.8)
        lst_celsius_map = lst_raw - 273.15
        lst_norm = normalise_temperature(lst_raw, t_min_kelvin=270.0, t_max_kelvin=330.0)

        records.append({
            "timestamp": ts,
            "lst_raw": lst_raw,
            "lst_celsius_map": lst_celsius_map,
            "lst_norm": lst_norm,
            "lst_mean_kelvin": float(lst_raw.mean()),
            "lst_mean_celsius": float(lst_celsius_map.mean()),
            "lst_std": float(lst_raw.std()),
            "is_flooded": bool(is_flooded),
        })

    return records
