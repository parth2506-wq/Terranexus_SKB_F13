"""
CarbonKarma — /satellite-data route.

Returns raw ingested satellite observations (S1, S2, LST, weather) without
running AI models. Useful for debugging ingestion and previewing raw data.

POST /satellite-data
Body (JSON):
  {
    "lat": float,           # required if no geojson
    "lon": float,
    "geojson": {...},       # optional GeoJSON Feature/Geometry
    "n_steps": int,         # default 10
    "step_days": int,       # default 10
    "start_date": "YYYY-MM-DD"  # optional
  }

Response:
  { sentinel1: [...], sentinel2: [...], lst: [...], weather: [...], timestamps: [...] }
"""

from __future__ import annotations

import logging

from flask import Blueprint, request, jsonify, Response

from utils.geo import parse_location
from utils.time_series import generate_date_range
from services.sentinel1 import fetch_sentinel1
from services.sentinel2 import fetch_sentinel2
from services.sentinel3_landsat import fetch_lst
from services.weather import fetch_weather

logger = logging.getLogger(__name__)

satellite_bp = Blueprint("satellite", __name__)


@satellite_bp.route("/satellite-data", methods=["POST"])
def satellite_data() -> Response:
    """Return raw satellite and weather observations for a location."""
    body = request.get_json(silent=True) or {}

    # ── Input validation ──────────────────────────────────────────────────
    lat = body.get("lat")
    lon = body.get("lon")
    geojson = body.get("geojson")

    if lat is None and lon is None and geojson is None:
        return jsonify({"error": "Provide 'lat'+'lon' or a 'geojson' polygon."}), 400

    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "'lat' and 'lon' must be numeric."}), 400

    n_steps = int(body.get("n_steps", 10))
    step_days = int(body.get("step_days", 10))
    start_date = body.get("start_date")

    n_steps = max(1, min(n_steps, 50))   # guard rails

    # ── Location ──────────────────────────────────────────────────────────
    try:
        location = parse_location(lat, lon, geojson)
    except Exception as exc:
        return jsonify({"error": f"Location parsing failed: {exc}"}), 400

    timestamps = generate_date_range(start=start_date, n_steps=n_steps, step_days=step_days)
    awd_pattern = [i % 12 < 7 for i in range(n_steps)]

    # ── Ingestion ─────────────────────────────────────────────────────────
    try:
        s1 = fetch_sentinel1(location["lat"], location["lon"], timestamps, awd_pattern=awd_pattern)
        s2 = fetch_sentinel2(location["lat"], location["lon"], timestamps, awd_pattern=awd_pattern)
        lst = fetch_lst(location["lat"], location["lon"], timestamps, awd_pattern=awd_pattern)
        wx = fetch_weather(location["lat"], location["lon"], timestamps)
    except Exception as exc:
        logger.exception("Ingestion error")
        return jsonify({"error": f"Data ingestion failed: {exc}"}), 500

    # Strip numpy arrays before JSON serialisation
    def _strip(records, keep_keys):
        return [{k: r[k] for k in keep_keys if k in r} for r in records]

    s1_out = _strip(s1, [
        "timestamp", "vv_mean", "vh_mean", "water_prob_mean", "phenology_stage", "is_flooded"
    ])
    s2_out = _strip(s2, [
        "timestamp", "ndvi_mean", "ndvi_std", "cloud_fraction", "phenology_stage", "is_flooded"
    ])
    lst_out = _strip(lst, [
        "timestamp", "lst_mean_kelvin", "lst_mean_celsius", "lst_std", "is_flooded"
    ])

    return jsonify({
        "status": "success",
        "location": {
            "lat": location["lat"],
            "lon": location["lon"],
            "bbox": list(location["bbox"]),
            "area_ha": location.get("area_ha"),
        },
        "timestamps": timestamps,
        "n_steps": n_steps,
        "step_days": step_days,
        "sentinel1": s1_out,
        "sentinel2": s2_out,
        "lst": lst_out,
        "weather": wx,
    })
