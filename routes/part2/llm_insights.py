"""
POST /llm-insights — Free-form AI-powered field insights via OpenRouter LLM.

Accepts a natural-language query about the farm and returns a structured
AI-generated answer enriched with live satellite + methane context.

Also exposes:
  POST /llm-insights/explain  — verbose verification explanation
  POST /llm-insights/alerts   — LLM-augmented alert narratives
  POST /llm-insights/certificate — certificate text generation
"""
from __future__ import annotations

import os
from flask import Blueprint, request, jsonify

from services.pipeline import run_full_pipeline
from services.part2.verification_engine import verify
from services.part2.credit_engine import calculate_credits, get_wallet
from services.part2.analytics_engine import generate_alerts, compute_farm_score, get_farm_profile
from services.part2.llm_service import (
    explain_verification,
    generate_alert_context,
    generate_certificate_text,
    answer_insight_query,
)

llm_bp = Blueprint("llm", __name__)


def _run_p1_mini(body: dict) -> tuple:
    """Run Part 1 with minimal steps for LLM context gathering."""
    lat     = body.get("lat")
    lon     = body.get("lon") if body.get("lon") is not None else body.get("lng")
    geojson = body.get("geojson")
    if lat is None and lon is None and geojson is None:
        return None, jsonify({"error": "Provide lat+lon (or lng) or geojson"}), 400
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return None, jsonify({"error": "lat/lon must be numeric"}), 400

    n_steps   = max(1, min(int(body.get("n_steps", 10)), 50))
    step_days = max(1, int(body.get("step_days", 10)))
    p1 = run_full_pipeline(lat=lat, lon=lon, geojson=geojson,
                           n_steps=n_steps, step_days=step_days, include_heatmaps=False)
    return p1, None, None


# ── POST /llm-insights ────────────────────────────────────────────────────

@llm_bp.route("/llm-insights", methods=["POST"])
def llm_insights():
    """
    Free-form query answering about the field.

    Body:
        lat, lon / geojson  — field location
        query               — natural language question (required)
        farm_id             — farm identifier (default: farm_001)
        n_steps             — observation steps
    """
    body  = request.get_json(silent=True) or {}
    query = body.get("query", "").strip()
    if not query:
        return jsonify({"error": "Provide a 'query' string."}), 400

    farm_id = body.get("farm_id", "farm_001")
    area_ha = float(body.get("area_ha", os.getenv("FARM_AREA_HA", "4.5")))

    p1, err_resp, err_code = _run_p1_mini(body)
    if err_resp:
        return err_resp, err_code

    if p1["location"].get("area_ha"):
        area_ha = p1["location"]["area_ha"]

    fusion_data  = p1["fusion_data"]
    awd_result   = p1["awd_result"]
    methane_data = p1["methane"]

    verification = verify(fusion_data, awd_result, methane_data, farm_id=farm_id)
    calculation  = calculate_credits(methane_data["aggregate"], area_ha=area_ha,
                                     verification_level=verification["level"])
    wallet       = get_wallet(farm_id)
    farm_score   = compute_farm_score(fusion_data, awd_result,
                                      methane_data["aggregate"], verification["confidence"])

    context = {
        "farm_id":          farm_id,
        "awd_status":       awd_result.get("awd_status"),
        "awd_cycles":       awd_result.get("cycles", 0),
        "credits_balance":  wallet["total_balance"],
        "credits_earned":   calculation["credits_earned"],
        "farm_score":       farm_score.get("overall_score"),
        "mean_ndvi":        round(sum(r.get("ndvi", 0) for r in fusion_data) / max(len(fusion_data), 1), 3),
        "mean_water":       round(sum(r.get("water_level", 0) for r in fusion_data) / max(len(fusion_data), 1), 3),
        "methane_category": methane_data["latest"].get("category", "medium"),
        "reduction_pct":    methane_data["aggregate"].get("total_reduction_pct", 0),
        "verification_level": verification["level"],
    }

    insight = answer_insight_query(query, context)

    return jsonify({
        "status":   "success",
        "farm_id":  farm_id,
        "location": p1["location"],
        "query":    query,
        "insight":  insight,
        "context_used": context,
        "source":   insight.get("source", "template"),
    })


# ── POST /llm-insights/explain ────────────────────────────────────────────

@llm_bp.route("/llm-insights/explain", methods=["POST"])
def llm_explain():
    """Verbose LLM explanation of the verification result."""
    body    = request.get_json(silent=True) or {}
    farm_id = body.get("farm_id", "farm_001")

    p1, err_resp, err_code = _run_p1_mini(body)
    if err_resp:
        return err_resp, err_code

    verification = verify(p1["fusion_data"], p1["awd_result"], p1["methane"], farm_id=farm_id)
    explanation  = explain_verification(verification, p1["methane"], p1["awd_result"])

    return jsonify({
        "status":       "success",
        "farm_id":      farm_id,
        "location":     p1["location"],
        "verification": {
            "level":       verification["level"],
            "confidence":  verification["confidence"],
            "explanation": verification["explanation"],
        },
        "llm_explanation": explanation,
    })


# ── POST /llm-insights/alerts ─────────────────────────────────────────────

@llm_bp.route("/llm-insights/alerts", methods=["POST"])
def llm_alerts():
    """Return LLM-enriched alert narratives for flooding / methane warnings."""
    body    = request.get_json(silent=True) or {}
    farm_id = body.get("farm_id", "farm_001")

    p1, err_resp, err_code = _run_p1_mini(body)
    if err_resp:
        return err_resp, err_code

    farm_score  = compute_farm_score(p1["fusion_data"], p1["awd_result"],
                                     p1["methane"]["aggregate"],
                                     verify(p1["fusion_data"], p1["awd_result"],
                                            p1["methane"], farm_id=farm_id)["confidence"])
    alerts_data = generate_alerts(p1["fusion_data"], p1["awd_result"],
                                  p1["methane"]["per_step"], farm_score)
    alert_ctx   = generate_alert_context(alerts_data.get("alerts", []), farm_id)

    return jsonify({
        "status":         "success",
        "farm_id":        farm_id,
        "location":       p1["location"],
        "alerts":         alerts_data,
        "llm_narratives": alert_ctx,
    })


# ── POST /llm-insights/certificate ───────────────────────────────────────

@llm_bp.route("/llm-insights/certificate", methods=["POST"])
def llm_certificate():
    """Generate an LLM-authored carbon credit certificate text."""
    body    = request.get_json(silent=True) or {}
    farm_id = body.get("farm_id", "farm_001")
    area_ha = float(body.get("area_ha", os.getenv("FARM_AREA_HA", "4.5")))

    p1, err_resp, err_code = _run_p1_mini(body)
    if err_resp:
        return err_resp, err_code

    if p1["location"].get("area_ha"):
        area_ha = p1["location"]["area_ha"]

    verification = verify(p1["fusion_data"], p1["awd_result"], p1["methane"], farm_id=farm_id)
    calculation  = calculate_credits(p1["methane"]["aggregate"], area_ha=area_ha,
                                     verification_level=verification["level"])
    wallet       = get_wallet(farm_id)
    farm_profile = get_farm_profile(farm_id)

    cert_text = generate_certificate_text(
        farm_profile=farm_profile,
        credits={"credits_earned": calculation["credits_earned"],
                 "usd_value": calculation["usd_value"],
                 "total_balance": wallet["total_balance"]},
        verification=verification,
    )

    return jsonify({
        "status":            "success",
        "farm_id":           farm_id,
        "location":          p1["location"],
        "certificate_text":  cert_text,
        "verification_level": verification["level"],
        "credits_earned":    calculation["credits_earned"],
        "fingerprint":       verification.get("fingerprint"),
    })
