"""POST /credits — Carbon credit computation and wallet management."""
from __future__ import annotations
import os
from flask import Blueprint, request, jsonify
from services.pipeline import run_full_pipeline
from services.part2.verification_engine import verify
from services.part2.credit_engine import (
    calculate_credits, issue_credits, get_wallet, compute_impact_metrics, retire_credits,
)

credits_bp = Blueprint("credits", __name__)

@credits_bp.route("/credits", methods=["GET", "POST"])
def credits():
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
    else:
        body = request.args.to_dict()
    lat      = body.get("lat")
    lon      = body.get("lon") if body.get("lon") is not None else body.get("lng")
    geojson  = body.get("geojson")
    if lat is None and lon is None and geojson is None and not body.get("farm_id"):
        return jsonify({"error": "Provide lat+lon (or lng), geojson, or farm_id"}), 400

    try:
        lat = float(lat) if lat is not None else 18.5204
        lon = float(lon) if lon is not None else 73.8567
    except (TypeError, ValueError):
        return jsonify({"error": "lat/lon must be numeric"}), 400

    n_steps   = max(1, min(int(body.get("n_steps", 12)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    farm_id   = body.get("farm_id", "farm_001")
    area_ha   = float(body.get("area_ha", os.getenv("FARM_AREA_HA", "4.5")))

    try:
        p1 = run_full_pipeline(lat=lat, lon=lon, geojson=geojson,
                               n_steps=n_steps, step_days=step_days, include_heatmaps=False)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Use area from polygon if available
    if p1["location"].get("area_ha"):
        area_ha = p1["location"]["area_ha"]

    verification = verify(p1["fusion_data"], p1["awd_result"], p1["methane"], farm_id=farm_id)
    calculation  = calculate_credits(p1["methane"]["aggregate"], area_ha=area_ha,
                                     verification_level=verification["level"])
    wallet_tx    = issue_credits(farm_id, calculation["credits_earned"], calculation, verification)
    wallet       = get_wallet(farm_id)
    impact       = compute_impact_metrics(calculation, area_ha)

    return jsonify({
        "status": "success",
        "farm_id": farm_id,
        "location": p1["location"],

        # Dashboard Integration aligned keys
        "total_co2e": wallet["total_balance"],
        "period_co2e": calculation["credits_earned"],
        "updated_at": p1.get("timestamps", [None])[-1] or "2026-04-18",

        # Original keys (backward compat)
        "credits_earned": calculation["credits_earned"],
        "usd_value": calculation["usd_value"],
        "total_balance": wallet["total_balance"],
        "calculation": calculation,
        "wallet": wallet,
        "wallet_tx": wallet_tx,
        "impact_metrics": impact,
        "verification_level": verification["level"],
    })


@credits_bp.route("/credits/wallet", methods=["GET"])
def credits_wallet():
    farm_id = request.args.get("farm_id", "farm_001")
    return jsonify(get_wallet(farm_id))


@credits_bp.route("/credits/retire", methods=["POST"])
def credits_retire():
    body    = request.get_json(silent=True) or {}
    farm_id = body.get("farm_id", "farm_001")
    amount  = float(body.get("amount", 0))
    reason  = body.get("reason", "certificate")
    if amount <= 0:
        return jsonify({"error": "amount must be > 0"}), 400
    result = retire_credits(farm_id, amount, reason)
    if "error" in result:
        return jsonify(result), 400
    return jsonify({"status": "success", **result})
