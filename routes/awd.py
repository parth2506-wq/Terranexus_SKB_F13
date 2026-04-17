"""
CarbonKarma — /awd-status route.

Runs the full pipeline and returns AWD detection results including:
  - Overall AWD status (active_awd / conventional / uncertain)
  - LSTM signal
  - Cycle count
  - Per-step water states
  - Irrigation vs rain event classification

POST /awd-status
Body (JSON):
  {
    "lat": float,
    "lon": float,
    "geojson": {...},
    "n_steps": int,       # default 12 (longer history helps AWD detection)
    "step_days": int,     # default 10
    "start_date": "YYYY-MM-DD"
  }
"""

from __future__ import annotations

import logging

from flask import Blueprint, request, jsonify, Response

from services.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)

awd_bp = Blueprint("awd", __name__)


@awd_bp.route("/awd-status", methods=["POST"])
def awd_status() -> Response:
    """Detect AWD practice and return cycle/event analysis."""
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

    # AWD detection benefits from longer time series
    n_steps = max(1, min(int(body.get("n_steps", 12)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    start_date = body.get("start_date")

    try:
        result = run_full_pipeline(
            lat=lat,
            lon=lon,
            geojson=geojson,
            n_steps=n_steps,
            step_days=step_days,
            start_date=start_date,
            include_heatmaps=False,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("AWD pipeline error")
        return jsonify({"error": f"Pipeline failed: {exc}"}), 500

    awd = result["awd_result"]

    return jsonify({
        "status": "success",
        "location": result["location"],
        "timestamps": result["timestamps"],
        "awd_status": awd["awd_status"],
        "confidence": awd["confidence"],
        "lstm_signal": awd["lstm_signal"],
        "cycles": awd["cycles"],
        "irrigation_events": awd["irrigation_events"],
        "rain_events": awd["rain_events"],
        "flood_dry_sequence": awd["flood_dry_sequence"],
        "per_step_status": awd["per_step_status"],
        "detection_params": {
            "flood_threshold": 0.55,
            "dry_threshold": 0.25,
            "min_cycle_days": 5,
        },
    })
