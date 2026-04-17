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


@awd_bp.route("/awd-status", methods=["GET", "POST"])
def awd_status() -> Response:
    """Detect AWD practice and return cycle/event analysis."""
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
    else:
        body = request.args.to_dict()

    lat = body.get("lat")
    lon = body.get("lon") if body.get("lon") is not None else body.get("lng")
    geojson = body.get("geojson")

    if lat is None and lon is None and geojson is None:
        return jsonify({"error": "Provide 'lat'+'lon' (or 'lng') or a 'geojson' polygon."}), 400

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

    # ── Map detected cycles to JSON objects for dashboard ─────────
    seq = awd.get("flood_dry_sequence", [])
    display_cycles = []
    current_cycle = None
    for i, step in enumerate(seq):
        if step["state"] == "dry":
            if current_cycle is None:
                current_cycle = {"type": "Flood → Dry (AWD)", "start": i + 1}
        elif step["state"] == "flooded" and current_cycle is not None:
            current_cycle["end"] = i + 1
            display_cycles.append(current_cycle)
            current_cycle = None
    if current_cycle:
        current_cycle["end"] = len(seq)
        display_cycles.append(current_cycle)

    # ── Synthetic Triple-Lock Validation ──────────────────────────
    has_active_awd = awd["awd_status"] == "active_awd"
    triple_lock = {
        "radar": awd["lstm_signal"] > 0.45 or awd["cycles"] > 0,
        "rainfall_shield": len(awd["rain_events"]) < 3,
        "metabolic": any(r.get("ndvi", 0) > 0.3 for r in result["fusion_data"])
    }

    # ── Hub-standard Explanation ──────────────────────────────────
    if has_active_awd:
        exp = f"Detected {awd['cycles']} wetting/drying cycles. Satellite radar confirms managed irrigation without significant interference from rainfall."
    elif awd["awd_status"] == "conventional":
        exp = "Paddy field appears continuously flooded. No significant drying events detected during the analysis period."
    else:
        exp = "Signal is uncertain. Patchy flooding detected, but managed AWD cycles are not clearly separable from background noise."

    return jsonify({
        "status": "success",
        "location": result["location"],
        "timestamps": result["timestamps"],

        # Dashboard Integration aligned keys
        "awd_detected": has_active_awd,
        "confidence": awd["confidence"],
        "cycles": display_cycles,
        "irrigation_events": len(awd["irrigation_events"]),
        "rainfall_events": len(awd["rain_events"]),
        "triple_lock": triple_lock,
        "explanation": exp,
        "water_series": [r.get("water_level", 0) for r in result["fusion_data"]],

        # Original keys (backward compat)
        "awd_status": awd["awd_status"],
        "lstm_signal": awd["lstm_signal"],
        "cycle_count": awd["cycles"],
        "per_step_status": awd["per_step_status"],
    })
