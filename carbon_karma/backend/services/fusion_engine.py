"""
CarbonKarma — Fusion Engine.

Merges all satellite and weather observations into a unified per-timestep
record and a spatial (patch-level) fusion array.

Pipeline per timestep:
  1. Align all patches to a common grid (CRS alignment)
  2. Compute derived quantities (soil moisture, water probability)
  3. Run CNN on SAR patch → water feature vector
  4. Assemble per-pixel fusion map
  5. Compile scalar summary record

Output schema per timestep:
  {
    location        : {lat, lon, bbox},
    timestamp       : ISO string,
    water_level     : float [0,1] — mean water probability
    ndvi            : float — mean NDVI
    temperature     : float — LST in °C
    rainfall        : float — mm
    soil_moisture   : float [0,1]
    flood_type      : "surface_water" | "irrigated" | "rain_fed" | "dry"
    awd_status      : placeholder (filled by AWD engine)
    pixel_fusion    : {water_prob, ndvi, lst_norm, soil_moisture} — (H×W) arrays
  }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from config import config
from services.preprocessing import align_to_common_grid, estimate_soil_moisture
from models.cnn_water import CNNWaterExtractor, run_cnn

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Flood type classification
# ---------------------------------------------------------------------------

def _classify_flood_type(
    water_prob: float,
    rainfall_mm: float,
    ndvi: float,
) -> str:
    """
    Rule-based flood type classification from scalar indicators.

    Rules:
      - water_prob > 0.65 and rainfall > 5 mm  → rain_fed
      - water_prob > 0.65 and rainfall ≤ 5 mm  → irrigated
      - water_prob 0.35–0.65                   → surface_water (partial)
      - water_prob < 0.35                       → dry
    """
    if water_prob > 0.65:
        if rainfall_mm > 5.0:
            return "rain_fed"
        else:
            return "irrigated"
    elif water_prob > 0.35:
        return "surface_water"
    else:
        return "dry"


# ---------------------------------------------------------------------------
# Main fusion function
# ---------------------------------------------------------------------------

def run_fusion(
    s1_records: List[Dict[str, Any]],
    s2_records: List[Dict[str, Any]],
    lst_records: List[Dict[str, Any]],
    weather_records: List[Dict[str, Any]],
    location: Dict[str, Any],
    cnn_model: Optional[CNNWaterExtractor] = None,
    patch_size: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Fuse all data sources into a unified observation list.

    All input record lists must be the same length and ordered by the same
    timestamps. In production, timestamps are aligned before this step.

    Parameters
    ----------
    s1_records      : Output of fetch_sentinel1()
    s2_records      : Output of fetch_sentinel2()
    lst_records     : Output of fetch_lst()
    weather_records : Output of fetch_weather()
    location        : Output of parse_location()
    cnn_model       : Pre-built CNNWaterExtractor (optional; built if None)
    patch_size      : Pixel resolution for spatial fusion

    Returns
    -------
    List of fused record dicts.
    """
    patch_size = patch_size or config.PATCH_SIZE

    if cnn_model is None:
        from models.cnn_water import build_cnn
        cnn_model = build_cnn()

    n = len(s1_records)
    if not (n == len(s2_records) == len(lst_records) == len(weather_records)):
        raise ValueError(
            f"All input record lists must be equal length. Got "
            f"s1={n}, s2={len(s2_records)}, lst={len(lst_records)}, "
            f"weather={len(weather_records)}"
        )

    fused_records: List[Dict[str, Any]] = []

    for i in range(n):
        s1 = s1_records[i]
        s2 = s2_records[i]
        lst = lst_records[i]
        wx = weather_records[i]

        timestamp = s1["timestamp"]

        # ── 1. Align patches to common grid ──────────────────────────────
        patches = {
            "vv": s1["vv_norm"],
            "vh": s1["vh_norm"],
            "red": s2["red"],
            "nir": s2["nir"],
            "ndvi": s2["ndvi_map"],
            "lst_norm": lst["lst_norm"],
            "water_prob": s1["water_prob_map"],
        }
        aligned = align_to_common_grid(patches, patch_size)

        # ── 2. Derived quantities ─────────────────────────────────────────
        soil_moisture_map = estimate_soil_moisture(
            aligned["vv"],
            aligned["vh"],
            aligned["ndvi"],
        )

        # ── 3. CNN water feature extraction ──────────────────────────────
        try:
            cnn_out = run_cnn(cnn_model, aligned["vv"], aligned["vh"])
        except Exception as exc:
            logger.warning("CNN inference failed at step %d: %s", i, exc)
            cnn_out = {
                "feature_vector": [0.0] * config.CNN_OUT_FEATURES,
                "water_score": float(s1["water_prob_mean"]),
            }

        # ── 4. Scalar summaries ───────────────────────────────────────────
        water_level = float(aligned["water_prob"].mean())
        ndvi_mean = float(aligned["ndvi"].mean())
        lst_celsius = float(lst["lst_mean_celsius"])
        lst_norm_scalar = float(aligned["lst_norm"].mean())
        rainfall_mm = float(wx["rainfall_mm"])
        soil_moisture_mean = float(soil_moisture_map.mean())

        # Rainfall normalisation for model input (0 → 0, 100 mm → 1)
        rainfall_norm = float(np.clip(rainfall_mm / 100.0, 0.0, 1.0))

        # LST normalisation for model input
        lst_celsius_norm = float(np.clip((lst_celsius - 15.0) / 45.0, 0.0, 1.0))

        flood_type = _classify_flood_type(water_level, rainfall_mm, ndvi_mean)

        # ── 5. Assemble fused record ──────────────────────────────────────
        fused_records.append({
            # Identifiers
            "location": {
                "lat": location["lat"],
                "lon": location["lon"],
                "bbox": list(location["bbox"]),
            },
            "timestamp": timestamp,

            # Scalar fusion outputs
            "water_level": round(water_level, 4),
            "ndvi": round(ndvi_mean, 4),
            "temperature": round(lst_celsius, 2),
            "rainfall": round(rainfall_mm, 2),
            "soil_moisture": round(soil_moisture_mean, 4),
            "flood_type": flood_type,

            # AWD placeholder (filled by AWD engine)
            "awd_status": None,

            # Model-ready scalars
            "water_prob_mean": round(water_level, 4),
            "ndvi_mean": round(ndvi_mean, 4),
            "lst_celsius_norm": round(lst_celsius_norm, 4),
            "rainfall_norm": round(rainfall_norm, 4),
            "soil_moisture_mean": round(soil_moisture_mean, 4),
            "vv_mean": round(float(s1["vv_mean"]), 4),
            "vh_mean": round(float(s1["vh_mean"]), 4),

            # CNN outputs
            "cnn_feature_vector": cnn_out["feature_vector"],
            "cnn_water_score": round(float(cnn_out["water_score"]), 4),

            # Spatial arrays (numpy — serialised downstream)
            "pixel_fusion": {
                "water_prob": aligned["water_prob"],
                "ndvi": aligned["ndvi"],
                "lst_norm": aligned["lst_norm"],
                "soil_moisture": soil_moisture_map,
            },

            # Metadata
            "phenology_stage": s1["phenology_stage"],
            "cloud_fraction": round(float(s2["cloud_fraction"]), 4),
        })

    return fused_records
