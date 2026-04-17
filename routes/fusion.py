"""
CarbonKarma — /fusion-data route.

Runs the full ingestion → preprocessing → CNN → fusion pipeline and returns
the unified per-timestep observation stream plus optional spatial heatmaps.

POST /fusion-data
Body (JSON):
  {
    "lat": float,
    "lon": float,
    "geojson": {...},          # optional
    "n_steps": int,            # default 10
    "step_days": int,          # default 10
    "start_date": "YYYY-MM-DD",
    "include_heatmaps": bool   # default true
  }

Response schema (per step):
  {
    location, timestamp, water_level, ndvi, temperature,
    rainfall, soil_moisture, flood_type, awd_status,
    cnn_water_score, phenology_stage, cloud_fraction
  }
"""

from __future__ import annotations

import logging

from flask import Blueprint, request, jsonify, Response

from services.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)

fusion_bp = Blueprint("fusion", __name__)


@fusion_bp.route("/fusion-data", methods=["POST"])
def fusion_data() -> Response:
    """Return fused multi-source observations for a field location."""
    body = request.get_json(silent=True) or {}

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

    n_steps = max(1, min(int(body.get("n_steps", 10)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    start_date = body.get("start_date")
    include_heatmaps = bool(body.get("include_heatmaps", True))

    try:
        result = run_full_pipeline(
            lat=lat,
            lon=lon,
            geojson=geojson,
            n_steps=n_steps,
            step_days=step_days,
            start_date=start_date,
            include_heatmaps=include_heatmaps,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Fusion pipeline error")
        return jsonify({"error": f"Pipeline failed: {exc}"}), 500

    # Build the fusion-specific response slice
    response = {
        "status": "success",
        "location": result["location"],
        "timestamps": result["timestamps"],
        "n_steps": result["n_steps"],
        "step_days": result["step_days"],
        "fusion_data": result["fusion_data"],
        "heatmaps": result.get("heatmaps", {}),
    }

    return jsonify(response)
