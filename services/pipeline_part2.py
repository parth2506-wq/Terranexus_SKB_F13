"""
CarbonKarma Part 2 — Master Pipeline (fixed: removed store_to_vector dependency)
Wraps Part 1 and adds: Verification → Credits → Analytics → LLM → Report → Storage
"""
from __future__ import annotations
import logging, os
import numpy as np
from typing import Any, Dict, List, Optional

from config import config
from services.pipeline import run_full_pipeline
from services.part2.verification_engine import verify
from services.part2.credit_engine import calculate_credits, issue_credits, get_wallet, compute_impact_metrics
from services.part2.analytics_engine import (
    compute_farm_score, comparative_analysis, historical_trends,
    generate_alerts, generate_predictions, field_segmentation,
    get_farm_profile, get_audit_trail,
)
from services.part2.llm_service import explain_verification, generate_report_narrative, generate_alert_context, answer_insight_query
from services.part2.report_generator import generate_report
from db.store import get_store

logger = logging.getLogger(__name__)


def _persist_history(farm_id: str, fusion_data: List[Dict]) -> None:
    store = get_store()
    for rec in fusion_data:
        store.save_observation(farm_id, {
            k: v for k, v in rec.items()
            if k not in ("cnn_feature_vector",)
        })


def run_part2_pipeline(
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    geojson: Optional[Dict] = None,
    farm_id: str = "farm_001",
    n_steps: int = 12,
    step_days: int = 10,
    start_date: Optional[str] = None,
    generate_pdf: bool = False,
    region: str = "south_asia",
    include_heatmaps: bool = False,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute full Part 1 + Part 2 pipeline and return enriched response."""

    # ── Part 1 ────────────────────────────────────────────────────────────
    logger.info("[Part2] Running Part 1 for farm=%s", farm_id)
    p1 = run_full_pipeline(
        lat=lat, lon=lon, geojson=geojson,
        n_steps=n_steps, step_days=step_days,
        start_date=start_date, include_heatmaps=include_heatmaps,
    )
    fusion_data  = p1["fusion_data"]
    awd_result   = p1["awd_result"]
    methane_data = p1["methane"]
    weather_recs = p1["satellite_data"]["weather"]
    location     = p1["location"]
    area_ha      = location.get("area_ha") or float(os.getenv("FARM_AREA_HA", "4.5"))

    # ── Farm profile ──────────────────────────────────────────────────────
    farm_profile = get_farm_profile(farm_id)
    farm_profile["farm_id"] = farm_id
    if not farm_profile.get("farm_area_ha"):
        farm_profile["farm_area_ha"] = area_ha

    # ── Persist observations ──────────────────────────────────────────────
    _persist_history(farm_id, fusion_data)

    # ── Verification ─────────────────────────────────────────────────────
    logger.info("[Part2] Verification…")
    verification = verify(fusion_data, awd_result, methane_data, farm_id=farm_id)

    # ── Credits ───────────────────────────────────────────────────────────
    logger.info("[Part2] Credits…")
    calculation = calculate_credits(
        methane_data["aggregate"], area_ha=area_ha,
        verification_level=verification["level"],
        season_days=methane_data["aggregate"].get("season_days"),
    )
    wallet_tx = issue_credits(farm_id, calculation["credits_earned"], calculation, verification)
    wallet    = get_wallet(farm_id)
    impact    = compute_impact_metrics(calculation, area_ha)

    credits_payload = {
        "credits_earned":   calculation["credits_earned"],
        "usd_value":        calculation["usd_value"],
        "total_balance":    wallet["total_balance"],
        "calculation":      calculation,
        "wallet_tx":        wallet_tx,
        "impact_metrics":   impact,
    }

    # ── Analytics ─────────────────────────────────────────────────────────
    logger.info("[Part2] Analytics…")
    farm_score  = compute_farm_score(fusion_data, awd_result, methane_data["aggregate"], verification["confidence"])
    comparative = comparative_analysis(methane_data["aggregate"], awd_result, region=region)
    trends      = historical_trends(farm_id, fusion_data)
    alerts_data = generate_alerts(fusion_data, awd_result, methane_data["per_step"], farm_score)
    predictions = generate_predictions(fusion_data, weather_recs, methane_data["per_step"])

    # Field segmentation from heatmap pixel arrays
    patch = config.PATCH_SIZE
    hm = p1.get("heatmaps", {})
    seg_pf = {}
    for band in ["water_prob", "ndvi", "lst_norm", "soil_moisture"]:
        if band in hm:
            pts = hm[band].get("data", [])
            arr = np.array([pt["value"] for pt in pts], dtype=np.float32)
            if arr.size == patch * patch:
                seg_pf[band] = arr.reshape(patch, patch)
    if not seg_pf:
        seg_pf = {k: np.full((patch, patch), 0.5, dtype=np.float32)
                  for k in ["water_prob", "ndvi", "lst_norm", "soil_moisture"]}

    segmentation = field_segmentation(seg_pf, location["lat"], location["lon"],
                                      bbox=location["bbox"], patch_size=patch)
    audit_trail  = get_audit_trail(farm_id)

    analytics_payload = {
        "farm_score": farm_score, "comparative": comparative,
        "historical_trends": trends, "alerts": alerts_data,
        "predictions": predictions, "field_segmentation": segmentation,
        "audit_trail": audit_trail,
    }

    # ── LLM ───────────────────────────────────────────────────────────────
    logger.info("[Part2] LLM…")
    llm_explanation = explain_verification(verification, methane_data, awd_result)
    alert_context   = generate_alert_context(alerts_data.get("alerts", []), farm_id)
    insight_answer  = None
    if query:
        insight_answer = answer_insight_query(query, {
            "farm_id": farm_id,
            "awd_status": awd_result.get("awd_status"),
            "credits_balance": wallet["total_balance"],
            "farm_score": farm_score.get("overall_score"),
        })

    # ── Report ────────────────────────────────────────────────────────────
    report_result = None
    if generate_pdf:
        logger.info("[Part2] Report…")
        narrative_out = generate_report_narrative({
            "farm_profile": farm_profile, "verification": verification,
            "credits": credits_payload, "awd": awd_result,
        })
        report_result = generate_report(
            farm_id=farm_id, farm_profile=farm_profile,
            verification=verification, awd_result=awd_result,
            methane_data=methane_data, credits_data=credits_payload,
            farm_score=farm_score, satellite_summary=p1.get("satellite_data"),
            narrative=narrative_out["narrative"],
            alerts=alerts_data.get("alerts", []),
        )

    # ── Audit log ─────────────────────────────────────────────────────────
    get_store().log_event(farm_id, "PIPELINE_RUN", "Part 2 pipeline completed", {
        "verification_level": verification["level"],
        "credits_earned":     calculation["credits_earned"],
        "awd_status":         awd_result["awd_status"],
        "farm_score":         farm_score["overall_score"],
    })

    return {
        "status": "success", "farm_id": farm_id,
        "location": location, "timestamps": p1["timestamps"],
        "satellite_data": p1["satellite_data"],
        "fusion_data": fusion_data,
        "awd_result": awd_result, "methane": methane_data,
        "farm_profile": farm_profile,
        "verification": verification,
        "credits": credits_payload, "wallet": wallet,
        "analytics": analytics_payload,
        "llm": {"verification_explanation": llm_explanation,
                "alert_context": alert_context,
                "insight_answer": insight_answer},
        "report": report_result,
        "heatmaps": p1.get("heatmaps", {}),
    }
