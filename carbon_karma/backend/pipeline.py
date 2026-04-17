"""
CarbonKarma — Master Pipeline Orchestrator.

This module is the single entry point for all route handlers. It:
  1. Parses location input (lat/lon or GeoJSON polygon)
  2. Generates timestamps for the requested time range
  3. Ingests satellite data (S1, S2, LST) and weather
  4. Runs preprocessing and CRS alignment inside each service
  5. Fuses all data (fusion_engine)
  6. Runs AWD detection (awd_engine) and LSTM
  7. Runs methane estimation (methane_engine)
  8. Builds heatmap-ready spatial outputs
  9. Returns a structured result dict

All heavy objects (CNN, LSTM, Methane models) are built once at startup
and shared via the ModelRegistry singleton to avoid per-request init cost.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from config import config
from utils.geo import parse_location, build_heatmap_grid, filter_points_in_polygon
#from utils.time_series import generate_date_range
from services.sentinel1 import fetch_sentinel1
from services.sentinel2 import fetch_sentinel2
from services.sentinel3_landsat import fetch_lst
from services.weather import fetch_weather
from services.fusion_engine import run_fusion
from services.awd_engine import detect_awd
from services.methane_engine import estimate_methane_per_step, compute_season_aggregate
from models.cnn_water import build_cnn
from models.lstm_awd import build_lstm
from models.methane_model import build_methane_model

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Model Registry (singleton warm-up)
# ---------------------------------------------------------------------------

class _ModelRegistry:
    """Lazy singleton that builds all models once."""

    _cnn = None
    _lstm = None
    _methane = None

    @classmethod
    def cnn(cls):
        if cls._cnn is None:
            logger.info("Building CNN model on %s…", config.MODEL_DEVICE)
            cls._cnn = build_cnn(device=config.MODEL_DEVICE)
        return cls._cnn

    @classmethod
    def lstm(cls):
        if cls._lstm is None:
            logger.info("Building LSTM model on %s…", config.MODEL_DEVICE)
            cls._lstm = build_lstm(device=config.MODEL_DEVICE)
        return cls._lstm

    @classmethod
    def methane(cls):
        if cls._methane is None:
            logger.info("Building Methane model on %s…", config.MODEL_DEVICE)
            cls._methane = build_methane_model(device=config.MODEL_DEVICE)
        return cls._methane


# Eagerly warm up models when module is first imported
def warmup_models():
    """Call once at app startup to pre-load all models."""
    _ModelRegistry.cnn()
    _ModelRegistry.lstm()
    _ModelRegistry.methane()
    logger.info("All models loaded and ready.")


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _serialise_fused(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Strip numpy arrays from fused records for JSON serialisation."""
    out = []
    for rec in records:
        r = {k: v for k, v in rec.items() if k != "pixel_fusion"}
        out.append(r)
    return out


def _build_heatmaps(
    fused_records: List[Dict[str, Any]],
    bbox: tuple,
    patch_size: int,
    polygon_coords: Optional[List],
) -> Dict[str, Any]:
    """
    Build heatmap arrays from the last time step's pixel fusion maps.
    Returns a dict of band → list of { lat, lon, value } for frontend rendering.
    """
    if not fused_records:
        return {}

    # Use the most recent time step for spatial heatmap
    latest = fused_records[-1]
    pf = latest.get("pixel_fusion", {})

    heatmaps: Dict[str, Any] = {}

    band_labels = {
        "water_prob": "Water Probability",
        "ndvi": "NDVI",
        "lst_norm": "Land Surface Temperature (norm)",
        "soil_moisture": "Soil Moisture",
    }

    for band_key, label in band_labels.items():
        arr = pf.get(band_key)
        if arr is None:
            continue
        grid = build_heatmap_grid(bbox, patch_size, arr)
        if polygon_coords:
            grid = filter_points_in_polygon(grid, polygon_coords)
        heatmaps[band_key] = {
            "label": label,
            "timestamp": latest["timestamp"],
            "data": grid,
        }

    return heatmaps


# ---------------------------------------------------------------------------
# Public pipeline entry point
# ---------------------------------------------------------------------------

def run_full_pipeline(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    geojson: Optional[Dict] = None,
    n_steps: int = 10,
    step_days: int = 10,
    start_date: Optional[str] = None,
    patch_size: Optional[int] = None,
    include_heatmaps: bool = True,
) -> Dict[str, Any]:
    """
    Execute the complete CarbonKarma Part-1 pipeline.

    Parameters
    ----------
    lat, lon        : Centroid of field (click input)
    geojson         : GeoJSON Feature or Geometry (polygon input)
    n_steps         : Number of satellite observation steps
    step_days       : Days between steps
    start_date      : ISO date for first observation (defaults to recent past)
    patch_size      : Spatial patch size in pixels
    include_heatmaps: Whether to build pixel-level heatmap outputs

    Returns
    -------
    Full pipeline result dict.
    """
    patch_size = patch_size or config.PATCH_SIZE

    # ── 1. Location parsing ───────────────────────────────────────────────
    location = parse_location(lat, lon, geojson)
    logger.info("Pipeline start: lat=%.4f lon=%.4f steps=%d", location["lat"], location["lon"], n_steps)

    # ── 2. Time axis ──────────────────────────────────────────────────────
    timestamps = generate_date_range(start=start_date, n_steps=n_steps, step_days=step_days)

    # Shared AWD pattern across all sensors (keeps scenes consistent)
    awd_pattern = [i % 12 < 7 for i in range(n_steps)]

    # ── 3. Data ingestion ─────────────────────────────────────────────────
    logger.debug("Ingesting Sentinel-1…")
    s1_records = fetch_sentinel1(
        location["lat"], location["lon"], timestamps,
        patch_size=patch_size, awd_pattern=awd_pattern
    )

    logger.debug("Ingesting Sentinel-2…")
    s2_records = fetch_sentinel2(
        location["lat"], location["lon"], timestamps,
        patch_size=patch_size, awd_pattern=awd_pattern
    )

    logger.debug("Ingesting LST…")
    lst_records = fetch_lst(
        location["lat"], location["lon"], timestamps,
        patch_size=patch_size, awd_pattern=awd_pattern
    )

    logger.debug("Fetching weather…")
    weather_records = fetch_weather(location["lat"], location["lon"], timestamps)

    # ── 4. Fusion ─────────────────────────────────────────────────────────
    logger.debug("Running fusion engine…")
    fused_records = run_fusion(
        s1_records, s2_records, lst_records, weather_records,
        location=location,
        cnn_model=_ModelRegistry.cnn(),
        patch_size=patch_size,
    )

    # ── 5. AWD detection ──────────────────────────────────────────────────
    logger.debug("Running AWD detection…")
    awd_result = detect_awd(
        fused_records,
        lstm_model=_ModelRegistry.lstm(),
        device=config.MODEL_DEVICE,
    )

    # ── 6. Methane estimation ─────────────────────────────────────────────
    logger.debug("Running methane engine…")
    methane_steps = estimate_methane_per_step(
        fused_records,
        methane_model=_ModelRegistry.methane(),
        device=config.MODEL_DEVICE,
    )
    methane_aggregate = compute_season_aggregate(methane_steps, step_days=step_days)

    # Latest step methane for summary
    latest_methane = methane_steps[-1] if methane_steps else {}

    # ── 7. Heatmaps ───────────────────────────────────────────────────────
    heatmaps: Dict[str, Any] = {}
    if include_heatmaps:
        logger.debug("Building heatmaps…")
        heatmaps = _build_heatmaps(
            fused_records,
            bbox=location["bbox"],
            patch_size=patch_size,
            polygon_coords=location.get("polygon_coords"),
        )

    # ── 8. Assemble result ────────────────────────────────────────────────
    serialised_fused = _serialise_fused(fused_records)

    return {
        "status": "success",
        "location": {
            "lat": location["lat"],
            "lon": location["lon"],
            "bbox": list(location["bbox"]),
            "area_ha": location.get("area_ha"),
            "polygon_coords": location.get("polygon_coords"),
        },
        "timestamps": timestamps,
        "n_steps": n_steps,
        "step_days": step_days,
        "satellite_data": {
            "sentinel1": [
                {
                    "timestamp": r["timestamp"],
                    "vv_mean": r["vv_mean"],
                    "vh_mean": r["vh_mean"],
                    "water_prob_mean": r["water_prob_mean"],
                    "phenology_stage": r["phenology_stage"],
                    "is_flooded": r["is_flooded"],
                }
                for r in s1_records
            ],
            "sentinel2": [
                {
                    "timestamp": r["timestamp"],
                    "ndvi_mean": r["ndvi_mean"],
                    "ndvi_std": r["ndvi_std"],
                    "cloud_fraction": r["cloud_fraction"],
                    "phenology_stage": r["phenology_stage"],
                }
                for r in s2_records
            ],
            "lst": [
                {
                    "timestamp": r["timestamp"],
                    "lst_mean_celsius": r["lst_mean_celsius"],
                    "lst_std": r["lst_std"],
                }
                for r in lst_records
            ],
            "weather": weather_records,
        },
        "fusion_data": serialised_fused,
        "awd_result": awd_result,
        "methane": {
            "per_step": methane_steps,
            "latest": latest_methane,
            "aggregate": methane_aggregate,
        },
        "heatmaps": heatmaps,
    }
