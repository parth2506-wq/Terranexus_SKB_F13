"""POST /verification — dMRV verification of field data."""
from __future__ import annotations
from flask import Blueprint, request, jsonify
from services.pipeline import run_full_pipeline
from services.part2.verification_engine import verify
from services.part2.llm_service import explain_verification

verification_bp = Blueprint("verification", __name__)

@verification_bp.route("/verification", methods=["GET", "POST"])
def verification():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
    else:
        body = request.args.to_dict()

    lat = body.get("lat")
    lon = body.get("lon") if body.get("lon") is not None else body.get("lng")
    geojson = body.get("geojson")

    if lat is None and lon is None and geojson is None and not body.get("farm_id"):
        return jsonify({"error": "Provide lat+lon (or lng), geojson, or farm_id"}), 400

    try:
        lat = float(lat) if lat is not None else 18.5204
        lon = float(lon) if lon is not None else 73.8567
    except (TypeError, ValueError):
        return jsonify({"error": "lat/lon must be numeric"}), 400

    n_steps  = max(1, min(int(body.get("n_steps", 12)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    farm_id  = body.get("farm_id", "farm_001")

    try:
        p1 = run_full_pipeline(lat=lat, lon=lon, geojson=geojson,
                               n_steps=n_steps, step_days=step_days,
                               include_heatmaps=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    result = verify(p1["fusion_data"], p1["awd_result"], p1["methane"], farm_id=farm_id)
    llm_exp = explain_verification(result, p1["methane"], p1["awd_result"])

    return jsonify({
        "status": "success",
        "farm_id": farm_id,
        "location": p1["location"],
        "verification": result,
        "llm_explanation": llm_exp,
        "awd_summary": {
            "awd_status": p1["awd_result"]["awd_status"],
            "cycles": p1["awd_result"]["cycles"],
            "confidence": p1["awd_result"]["confidence"],
        },
        "methane_summary": p1["methane"]["aggregate"],
    })
