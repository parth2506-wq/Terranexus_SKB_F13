"""
CarbonKarma — Sentinel-1 SAR data ingestion service.

Simulates Sentinel-1 C-band SAR backscatter (VV / VH polarisations) over a
paddy rice field at multiple time steps. In production, this layer would call
the Sentinel Hub Process API or a STAC catalogue to fetch real GRD products.

Simulation physics:
  - Flooded paddy  → low VV (−18 to −12 dB), low VH (−22 to −16 dB)
  - Vegetated paddy → VV rises (−12 to −6 dB) as biomass increases
  - Soil drying     → VV rises toward −8 dB
  - Gaussian spatial variation to mimic field heterogeneity

Outputs are normalised to [0, 1] for model consumption.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from config import config
from services.preprocessing import lee_filter, compute_water_probability


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _db_to_linear(db_value: float) -> float:
    """Convert decibel backscatter to linear scale (σ⁰)."""
    return 10.0 ** (db_value / 10.0)


def _simulate_backscatter_patch(
    patch_size: int,
    vv_db_mean: float,
    vh_db_mean: float,
    spatial_std: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a spatially correlated backscatter patch (H × W) for VV and VH.

    Uses a smooth Gaussian base field plus random speckle.
    """
    # Smooth spatial base (field heterogeneity)
    base = np.random.normal(0, spatial_std, (patch_size, patch_size)).astype(np.float32)

    # Low-frequency smoothing to simulate correlated field variation
    kernel_size = max(3, patch_size // 8)
    if kernel_size % 2 == 0:
        kernel_size += 1
    import cv2
    base = cv2.GaussianBlur(base, (kernel_size, kernel_size), 0)

    # Linear backscatter
    vv_linear = _db_to_linear(vv_db_mean) + base * _db_to_linear(vv_db_mean)
    vh_linear = _db_to_linear(vh_db_mean) + base * _db_to_linear(vh_db_mean) * 0.8

    vv_linear = np.maximum(vv_linear, 1e-6)
    vh_linear = np.maximum(vh_linear, 1e-6)

    return vv_linear.astype(np.float32), vh_linear.astype(np.float32)


def _phenology_state(day_of_season: int) -> str:
    """
    Map day-of-season index to a paddy rice phenology stage.
    Typical season: transplanting (0-15), tillering (16-40),
    heading (41-65), ripening (66-90), harvest (91+).
    """
    if day_of_season < 16:
        return "transplanting"
    elif day_of_season < 41:
        return "tillering"
    elif day_of_season < 66:
        return "heading"
    elif day_of_season < 91:
        return "ripening"
    else:
        return "harvest"


def _backscatter_params_for_stage(
    stage: str,
    is_flooded: bool,
) -> tuple[float, float]:
    """Return (vv_db_mean, vh_db_mean) for a given phenology stage and flood state."""
    table = {
        # stage: (flooded_vv, flooded_vh, dry_vv, dry_vh)
        "transplanting": (-18.0, -22.0, -14.0, -18.0),
        "tillering":     (-16.0, -20.0, -12.0, -17.0),
        "heading":       (-10.0, -15.0,  -8.0, -13.0),
        "ripening":      ( -8.0, -13.0,  -6.0, -11.0),
        "harvest":       (-12.0, -17.0, -10.0, -15.0),
    }
    row = table.get(stage, (-14.0, -19.0, -10.0, -15.0))
    vv = row[0] if is_flooded else row[2]
    vh = row[1] if is_flooded else row[3]
    return vv, vh


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_sentinel1(
    lat: float,
    lon: float,
    timestamps: List[str],
    patch_size: Optional[int] = None,
    awd_pattern: Optional[List[bool]] = None,
) -> List[Dict[str, Any]]:
    """
    Return a list of Sentinel-1 observations, one per timestamp.

    Parameters
    ----------
    lat, lon      : Field centroid.
    timestamps    : Ordered list of ISO date strings.
    patch_size    : Spatial patch dimensions (pixels).
    awd_pattern   : Optional override list of bool (True=flooded) matching
                    the length of timestamps. If None, a realistic AWD
                    alternating pattern is synthesised.

    Each returned record contains:
        timestamp       : ISO string
        vv_raw          : (H×W) raw backscatter patch (float32)
        vv_filtered     : (H×W) Lee-filtered VV patch
        vh_raw          : (H×W) raw VH patch
        vh_filtered     : (H×W) Lee-filtered VH patch
        vv_mean         : scalar mean of filtered VV
        vh_mean         : scalar mean of filtered VH
        water_prob_map  : (H×W) per-pixel water probability
        water_prob_mean : scalar mean water probability
        phenology_stage : string
        is_flooded      : bool (simulated ground truth)
    """
    patch_size = patch_size or config.PATCH_SIZE
    n = len(timestamps)

    # Build a realistic AWD flood pattern if not provided
    if awd_pattern is None:
        # Flood for ~7 days, dry for ~5 days, repeat
        awd_pattern = []
        for i in range(n):
            cycle_pos = i % 12          # 12-step cycle
            awd_pattern.append(cycle_pos < 7)   # 7 flooded, 5 dry

    records: List[Dict[str, Any]] = []

    for idx, ts in enumerate(timestamps):
        is_flooded = awd_pattern[idx % len(awd_pattern)]
        day_of_season = idx * 10          # assume 10-day steps
        stage = _phenology_state(day_of_season)
        vv_db, vh_db = _backscatter_params_for_stage(stage, is_flooded)

        # Add slight temporal trend noise
        vv_db += np.random.normal(0, 0.5)
        vh_db += np.random.normal(0, 0.4)

        vv_raw, vh_raw = _simulate_backscatter_patch(patch_size, vv_db, vh_db)

        # Lee-filter to reduce speckle
        vv_filtered = lee_filter(vv_raw, window_size=5)
        vh_filtered = lee_filter(vh_raw, window_size=5)

        # Normalise to [0, 1] by mapping typical σ⁰ range to unit interval
        # Typical paddy range: 0.006 (−22 dB) to 0.25 (−6 dB)
        vv_norm = np.clip((vv_filtered - 0.006) / (0.25 - 0.006), 0.0, 1.0)
        vh_norm = np.clip((vh_filtered - 0.003) / (0.15 - 0.003), 0.0, 1.0)

        water_prob_map = compute_water_probability(
            vv_norm - 0.5,   # shift back to roughly dB-like range for threshold
            vh_norm - 0.6,
        )
        if is_flooded:
            # Boost water probability for flooded pixels
            boost = np.random.uniform(0.1, 0.3, water_prob_map.shape).astype(np.float32)
            water_prob_map = np.clip(water_prob_map + boost, 0.0, 1.0)

        records.append({
            "timestamp": ts,
            "vv_raw": vv_raw,
            "vv_filtered": vv_filtered,
            "vh_raw": vh_raw,
            "vh_filtered": vh_filtered,
            "vv_norm": vv_norm,
            "vh_norm": vh_norm,
            "vv_mean": float(vv_norm.mean()),
            "vh_mean": float(vh_norm.mean()),
            "water_prob_map": water_prob_map,
            "water_prob_mean": float(water_prob_map.mean()),
            "phenology_stage": stage,
            "is_flooded": bool(is_flooded),
        })

    return records
