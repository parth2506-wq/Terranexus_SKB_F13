"""POST /analytics — Full analytics suite (8 modules)."""
from __future__ import annotations
import os
import numpy as np
from flask import Blueprint, request, jsonify
from config import config
from services.pipeline import run_full_pipeline
from services.part2.verification_engine import verify
from services.part2.credit_engine import calculate_credits, compute_impact_metrics
from services.part2.analytics_engine import (
    compute_farm_score, comparative_analysis, historical_trends,
    generate_alerts, generate_predictions, field_segmentation,
    get_farm_profile, get_audit_trail,
)
from services.part2.llm_service import generate_alert_context

analytics_bp = Blueprint("analytics", __name__)

@analytics_bp.route("/analytics", methods=["POST"])
def analytics():
    body     = request.get_json(silent=True) or {}
    lat      = body.get("lat"); lon = body.get("lon"); geojson = body.get("geojson")
    if lat is None and lon is None and geojson is None:
        return jsonify({"error": "Provide lat+lon or geojson"}), 400
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "lat/lon must be numeric"}), 400

    n_steps   = max(1, min(int(body.get("n_steps", 12)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    farm_id   = body.get("farm_id", "farm_001")
    region    = body.get("region", "south_asia")
    area_ha   = float(body.get("area_ha", os.getenv("FARM_AREA_HA", "4.5")))
    include_hm = bool(body.get("include_heatmaps", False))

    try:
        p1 = run_full_pipeline(lat=lat, lon=lon, geojson=geojson,
                               n_steps=n_steps, step_days=step_days,
                               include_heatmaps=include_hm)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if p1["location"].get("area_ha"):
        area_ha = p1["location"]["area_ha"]

    fusion_data  = p1["fusion_data"]
    awd_result   = p1["awd_result"]
    methane_data = p1["methane"]
    weather_recs = p1["satellite_data"]["weather"]

    verification = verify(fusion_data, awd_result, methane_data, farm_id=farm_id)
    calculation  = calculate_credits(methane_data["aggregate"], area_ha=area_ha,
                                     verification_level=verification["level"])
    impact       = compute_impact_metrics(calculation, area_ha)

    # 1. Farm score
    farm_score = compute_farm_score(fusion_data, awd_result, methane_data["aggregate"],
                                    verification["confidence"])
    # 2. Comparative
    comparative = comparative_analysis(methane_data["aggregate"], awd_result, region=region)
    # 3. Historical trends
    trends = historical_trends(farm_id, fusion_data)
    # 4. Alerts
    alerts_data = generate_alerts(fusion_data, awd_result, methane_data["per_step"], farm_score)
    alert_ctx   = generate_alert_context(alerts_data.get("alerts", []), farm_id)
    # 5. Predictions
    predictions = generate_predictions(fusion_data, weather_recs, methane_data["per_step"])
    # 6. Field segmentation
    patch = config.PATCH_SIZE
    hm = p1.get("heatmaps", {})
    seg_pf = {}
    for band in ["water_prob","ndvi","lst_norm","soil_moisture"]:
        if band in hm:
            pts = hm[band].get("data", [])
            arr = np.array([pt["value"] for pt in pts], dtype=np.float32)
            if arr.size == patch * patch:
                seg_pf[band] = arr.reshape(patch, patch)
    if not seg_pf:
        seg_pf = {k: np.full((patch,patch), 0.5, dtype=np.float32)
                  for k in ["water_prob","ndvi","lst_norm","soil_moisture"]}
    segmentation = field_segmentation(seg_pf, p1["location"]["lat"], p1["location"]["lon"],
                                      bbox=p1["location"]["bbox"], patch_size=patch)
    # 7. Impact metrics (already computed)
    # 8. Farm profile
    farm_profile = get_farm_profile(farm_id)
    # 9. Audit trail
    audit = get_audit_trail(farm_id)

    return jsonify({
        "status": "success",
        "farm_id": farm_id,
        "location": p1["location"],
        "timestamps": p1["timestamps"],

        # 1
        "farm_score": farm_score,
        # 2
        "comparative_analysis": comparative,
        # 3
        "historical_trends": trends,
        # 4
        "alerts": {**alerts_data, "llm_context": alert_ctx},
        # 5
        "predictions": predictions,
        # 6
        "field_segmentation": segmentation,
        # 7
        "impact_metrics": impact,
        # 8
        "farm_profile": farm_profile,
        # 9
        "audit_trail": audit,

        # Supporting data
        "verification_summary": {
            "level": verification["level"],
            "confidence": verification["confidence"],
        },
        "credits_earned": calculation["credits_earned"],
    })
