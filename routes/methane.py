"""
CarbonKarma — /methane route.

Runs the full pipeline and returns per-step and season-aggregate methane
flux estimates.

POST /methane
Body (JSON):
  {
    "lat": float,
    "lon": float,
    "geojson": {...},
    "n_steps": int,        # default 10
    "step_days": int,      # default 10
    "start_date": "YYYY-MM-DD"
  }

Response:
  {
    latest        : { timestamp, methane, category, reduction_percent }
    per_step      : [ { timestamp, methane, category, reduction_percent }, ... ]
    aggregate     : { season_total_kg_ha, mean_daily_flux, total_reduction_pct, ... }
    awd_status    : string
  }
"""

from __future__ import annotations

import logging

from flask import Blueprint, request, jsonify, Response

from services.pipeline import run_full_pipeline

logger = logging.getLogger(__name__)

methane_bp = Blueprint("methane", __name__)


@methane_bp.route("/methane", methods=["GET", "POST"])
def methane() -> Response:
    """Return methane flux estimates for a paddy field location."""
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

    n_steps = max(1, min(int(body.get("n_steps", 10)), 50))
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
        logger.exception("Methane pipeline error")
        return jsonify({"error": f"Pipeline failed: {exc}"}), 500

    methane_data = result["methane"]

    methane_data = result["methane"]
    latest = methane_data["latest"]
    agg = methane_data["aggregate"]

    return jsonify({
        "status": "success",
        "location": result["location"],

        # Dashboard Integration aligned keys
        "flux_kg_per_day": latest.get("methane", 0),
        "methane_flux": latest.get("methane", 0),
        "category": latest.get("category", "Medium"),
        "reduction_pct": agg.get("total_reduction_pct", 0),
        "ndvi": result["fusion_data"][-1].get("ndvi") if result["fusion_data"] else 0.5,
        "ef": 0.05,
        "k_factor": 1.12,
        "delta_temp": round(result["fusion_data"][-1].get("temperature", 30) - 25, 2) if result["fusion_data"] else 5.0,
        "vs_regional": f"{agg.get('total_reduction_pct', 0)}% below regional average",
        "baseline": 2.65,
        "time_series": [r.get("methane", 0) for r in methane_data["per_step"]],

        # Original keys (backward compat)
        "awd_status": result["awd_result"]["awd_status"],
        "awd_cycles": result["awd_result"]["cycles"],
        "methane_raw": methane_data,
        "units": {
            "methane": "mg CH4 / m² / day",
            "season_total_kg_ha": "kg CH4 / ha",
        }
    })
