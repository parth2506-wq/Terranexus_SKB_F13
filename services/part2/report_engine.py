"""
CarbonKarma Part 2 — Report Engine

Assembles a comprehensive, structured JSON report covering:
  - Satellite data summary
  - AWD analysis
  - Methane estimation
  - Verification result
  - Carbon credits
  - Farm score & analytics
  - Impact metrics
  - LLM-generated narrative

Report is persisted to the memory store and returned as a JSON dict
suitable for frontend rendering or PDF export.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from db.store import get_store
from services.part2.llm_service import generate_report_narrative, generate_certificate_text


def generate_report(
    farm_id: str,
    location: Dict,
    timestamps: List[str],
    satellite_summary: Dict,
    fusion_data: List[Dict],
    awd_result: Dict,
    methane_result: Dict,
    verification_result: Dict,
    credit_result: Dict,
    farm_score: Dict,
    comparative: Dict,
    historical: Dict,
    alerts: Dict,
    predictions: Dict,
    impact_metrics: Dict,
    farm_profile: Dict,
    include_narrative: bool = True,
) -> Dict[str, Any]:
    """
    Assemble a complete CarbonKarma monitoring report.

    Parameters
    ----------
    All parameters are the direct outputs of their respective engines.

    Returns
    -------
    Full report dict with report_id, all sections, and LLM narrative.
    """
    report_id  = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc).isoformat()
    store      = get_store()

    # ── LLM narrative ─────────────────────────────────────────────────────
    narrative_ctx = {
        "farm_id":        farm_id,
        "awd_status":     awd_result.get("awd_status"),
        "credits_balance": credit_result.get("total_balance", 0),
        "farm_score":     farm_score.get("overall_score", 0),
        "verification_status": verification_result.get("status"),
        "verification_level":  verification_result.get("level"),
        "mean_daily_flux":     methane_result.get("aggregate", {}).get("mean_daily_flux"),
        "total_reduction_pct": methane_result.get("aggregate", {}).get("total_reduction_pct"),
        "season_total_kg_ha":  methane_result.get("aggregate", {}).get("season_total_kg_ha"),
    }

    if include_narrative:
        narrative_out = generate_report_narrative(narrative_ctx)
        narrative = narrative_out.get("narrative", "")
        narrative_source = narrative_out.get("source", "template")
    else:
        narrative = ""
        narrative_source = "disabled"

    # ── Certificate text ──────────────────────────────────────────────────
    cert_text = ""
    if verification_result.get("status") in ("GOLD", "SILVER", "BRONZE"):
        try:
            cert_out  = generate_certificate_text(farm_profile, credit_result, verification_result)
            cert_text = cert_out.get("certificate", "")
        except Exception:
            cert_text = ""

    # ── Methane per-step timeline ─────────────────────────────────────────
    methane_timeline = []
    for step in methane_result.get("per_step", []):
        methane_timeline.append({
            "timestamp":        step.get("timestamp"),
            "methane":          step.get("methane"),
            "category":         step.get("category"),
            "reduction_percent": step.get("reduction_percent"),
        })

    # ── Fusion summary ────────────────────────────────────────────────────
    fusion_summary = []
    for r in fusion_data:
        fusion_summary.append({
            "timestamp":    r.get("timestamp"),
            "water_level":  r.get("water_level"),
            "ndvi":         r.get("ndvi"),
            "temperature":  r.get("temperature"),
            "rainfall":     r.get("rainfall"),
            "soil_moisture": r.get("soil_moisture"),
            "flood_type":   r.get("flood_type"),
            "awd_status":   r.get("awd_status"),
        })

    # ── Assemble full report ──────────────────────────────────────────────
    report: Dict[str, Any] = {
        "report_id":      report_id,
        "report_type":    "carbon_monitoring",
        "generated_at":   generated_at,
        "farm_id":        farm_id,
        "report_period":  {
            "start": timestamps[0] if timestamps else None,
            "end":   timestamps[-1] if timestamps else None,
            "n_observations": len(timestamps),
        },

        # Section 1: Location
        "location": {
            "lat":        location.get("lat"),
            "lon":        location.get("lon"),
            "bbox":       location.get("bbox"),
            "area_ha":    location.get("area_ha"),
        },

        # Section 2: Farm profile
        "farm_profile": farm_profile,

        # Section 3: Satellite data summary
        "satellite_data": satellite_summary,

        # Section 4: AWD analysis
        "awd_analysis": {
            "awd_status":      awd_result.get("awd_status"),
            "confidence":      awd_result.get("confidence"),
            "lstm_signal":     awd_result.get("lstm_signal"),
            "cycles":          awd_result.get("cycles"),
            "irrigation_events": awd_result.get("irrigation_events", []),
            "rain_events":     awd_result.get("rain_events", []),
            "flood_dry_sequence": awd_result.get("flood_dry_sequence", []),
        },

        # Section 5: Methane estimation
        "methane": {
            "latest":     methane_result.get("latest"),
            "aggregate":  methane_result.get("aggregate"),
            "timeline":   methane_timeline,
            "units": {
                "methane": "mg CH4 / m² / day",
                "season_total_kg_ha": "kg CH4 / ha",
            },
        },

        # Section 6: Verification
        "verification": {
            "status":         verification_result.get("status"),
            "level":          verification_result.get("level"),
            "confidence":     verification_result.get("confidence"),
            "data_integrity": verification_result.get("data_integrity"),
            "fingerprint":    verification_result.get("fingerprint"),
            "checks":         verification_result.get("checks", {}),
            "explanation":    verification_result.get("explanation"),
            "timestamp":      verification_result.get("timestamp"),
        },

        # Section 7: Carbon credits
        "credits": credit_result,

        # Section 8: Farm score & analytics
        "analytics": {
            "farm_score":   farm_score,
            "comparative":  comparative,
            "historical":   historical,
        },

        # Section 9: Alerts & predictions
        "alerts_and_predictions": {
            "alerts":          alerts.get("alerts", []),
            "recommendations": alerts.get("recommendations", []),
            "insights":        alerts.get("insights", []),
            "predictions":     predictions,
        },

        # Section 10: Impact metrics
        "impact": impact_metrics,

        # Section 11: Fusion detail
        "fusion_timeline": fusion_summary,

        # Section 12: LLM narrative
        "narrative": {
            "text":   narrative,
            "source": narrative_source,
        },

        # Section 13: Certificate
        "certificate": cert_text,
    }

    # ── Persist report ────────────────────────────────────────────────────
    try:
        store.save_report(farm_id, report)
        store.log_event(
            farm_id=farm_id,
            event_type="REPORT_GENERATED",
            description=f"Report {report_id} generated. Status: {verification_result.get('status')}.",
            data={"report_id": report_id, "verification_level": verification_result.get("level")},
        )
    except Exception:
        pass

    return report
