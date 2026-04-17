"""
CarbonKarma Part 2 — LLM Service (OpenRouter).

Uses OpenRouter's unified API to call open-source LLMs for:
  1. Explanation of verification results in plain language
  2. Automated MRV report narrative generation
  3. Alert context and agronomic advice
  4. Carbon certificate text generation

Falls back to a deterministic template engine when:
  - OPENROUTER_API_KEY is not set
  - API call fails (network, quota, etc.)

All prompts are structured to produce JSON-safe, concise outputs.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import requests

from config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Core API call
# ---------------------------------------------------------------------------

def _call_openrouter(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 600,
    temperature: float = 0.3,
) -> Optional[str]:
    """
    Call OpenRouter chat completions API.
    Returns the assistant's text content or None on failure.
    """
    if not config.OPENROUTER_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://carbonkarma.io",
        "X-Title": "CarbonKarma dMRV",
    }
    body = {
        "model": config.OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(
            config.OPENROUTER_BASE_URL,
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("OpenRouter call failed: %s — using template fallback.", exc)
        return None


# ---------------------------------------------------------------------------
# Template fallbacks (deterministic, always available)
# ---------------------------------------------------------------------------

def _template_verification_explanation(
    verification: Dict,
    methane: Dict,
    awd: Dict,
) -> str:
    level  = verification.get("level", "BRONZE")
    conf   = verification.get("confidence", 0.5)
    cycles = awd.get("cycles", 0)
    flux   = methane.get("aggregate", {}).get("mean_daily_flux", 250)
    reduct = methane.get("aggregate", {}).get("total_reduction_pct", 0)

    emoji = {"GOLD": "🥇", "SILVER": "🥈", "BRONZE": "🥉", "FAILED": "❌"}.get(level, "")
    return (
        f"{emoji} Your field has achieved **{level} verification** with a confidence score of "
        f"{conf:.0%}. Satellite observations recorded {cycles} AWD (Alternate Wetting & Drying) "
        f"cycles, with an average methane flux of {flux:.0f} mg CH₄/m²/day — "
        f"a {reduct:.1f}% reduction compared to conventional continuous flooding. "
        f"{'You are eligible for carbon credit issuance.' if level != 'FAILED' else 'Address data quality issues to qualify for credits.'}"
    )


def _template_report_narrative(context: Dict) -> str:
    farm   = context.get("farm_profile", {})
    verif  = context.get("verification", {})
    cred   = context.get("credits", {})
    awd    = context.get("awd", {})

    return (
        f"## Executive Summary\n\n"
        f"This report covers the satellite-based carbon monitoring of **{farm.get('farmer_name', 'the farm')}** "
        f"({farm.get('farm_area_ha', '?')} ha, {farm.get('crop_type', 'paddy rice')}) during the "
        f"{farm.get('season', 'current season')} season.\n\n"
        f"**Verification Result:** {verif.get('level', 'N/A')} (confidence {verif.get('confidence', 0):.0%})\n\n"
        f"**AWD Practice:** {awd.get('cycles', 0)} cycles detected. Status: {awd.get('awd_status', 'unknown')}.\n\n"
        f"**Carbon Credits Earned:** {cred.get('credits_earned', 0):.3f} tCO₂e "
        f"(USD {cred.get('usd_value', 0):.2f} at ${config.CREDIT_PRICE_USD}/credit).\n\n"
        f"**Key Finding:** {verif.get('explanation', '')}"
    )


def _template_alert_context(alerts: List[Dict]) -> str:
    if not alerts:
        return "No active alerts. Field conditions are within normal parameters."
    high = [a for a in alerts if a.get("severity") == "HIGH"]
    msg = f"⚠️ {len(alerts)} active alert(s), {len(high)} high-severity. "
    for a in alerts[:3]:
        msg += f"\n• [{a['severity']}] {a['message']}"
    return msg


def _template_certificate_text(farm: Dict, credits: Dict, verification: Dict) -> str:
    return (
        f"CARBON CREDIT CERTIFICATE\n"
        f"{'=' * 50}\n"
        f"Issued to : {farm.get('farmer_name', 'Unknown')}\n"
        f"Farm ID   : {farm.get('farm_id', 'N/A')}\n"
        f"Location  : {farm.get('farm_location', 'N/A')}\n"
        f"Area      : {farm.get('farm_area_ha', '?')} hectares\n"
        f"Season    : {farm.get('season', 'N/A')}\n"
        f"Crop      : {farm.get('crop_type', 'Paddy')}\n"
        f"\nCredits Issued : {credits.get('credits_earned', 0):.4f} tCO₂e\n"
        f"USD Value      : ${credits.get('usd_value', 0):.2f}\n"
        f"Verification   : {verification.get('level', 'N/A')} "
        f"(confidence {verification.get('confidence', 0):.0%})\n"
        f"Fingerprint    : {verification.get('fingerprint', 'N/A')[:32]}...\n"
        f"\nMethodology: IPCC AR6 GWP-100, dMRV satellite remote sensing,\n"
        f"CarbonKarma AWD detection protocol v1.0\n"
        f"{'=' * 50}\n"
        f"This certificate is generated by CarbonKarma dMRV Platform.\n"
        f"Verify at: https://carbonkarma.io/verify/{verification.get('fingerprint', '')[:16]}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_BASE = (
    "You are CarbonKarma, an expert in paddy rice carbon accounting, "
    "satellite remote sensing, and IPCC-compliant methane verification. "
    "Be concise, factual, and helpful. Respond in 2-4 sentences unless asked for more."
)


def explain_verification(
    verification: Dict,
    methane: Dict,
    awd: Dict,
) -> Dict[str, str]:
    """Generate a plain-language explanation of the verification result."""
    user_prompt = (
        f"Explain this MRV verification result to a farmer:\n"
        f"Level={verification.get('level')}, "
        f"Confidence={verification.get('confidence'):.0%}, "
        f"AWD cycles={awd.get('cycles')}, "
        f"Mean CH4 flux={methane.get('aggregate',{}).get('mean_daily_flux',0):.0f} mg/m2/day, "
        f"Reduction={methane.get('aggregate',{}).get('total_reduction_pct',0):.1f}%."
    )
    llm_text = _call_openrouter(SYSTEM_PROMPT_BASE, user_prompt, max_tokens=250)
    text = llm_text or _template_verification_explanation(verification, methane, awd)
    return {"explanation": text, "source": "llm" if llm_text else "template"}


def generate_report_narrative(context: Dict) -> Dict[str, str]:
    """Generate executive summary narrative for the PDF report."""
    user_prompt = (
        f"Write a 3-paragraph executive summary for a carbon credit MRV report. "
        f"Farm: {context.get('farm_profile', {}).get('farmer_name', 'Unknown')}, "
        f"Season: {context.get('farm_profile', {}).get('season', 'N/A')}, "
        f"Verification: {context.get('verification', {}).get('level', 'N/A')}, "
        f"Credits: {context.get('credits', {}).get('credits_earned', 0):.3f} tCO2e, "
        f"AWD cycles: {context.get('awd', {}).get('cycles', 0)}."
    )
    llm_text = _call_openrouter(SYSTEM_PROMPT_BASE, user_prompt, max_tokens=500)
    text = llm_text or _template_report_narrative(context)
    return {"narrative": text, "source": "llm" if llm_text else "template"}


def generate_alert_context(alerts: List[Dict], farm_id: str) -> Dict[str, str]:
    """Provide agronomic context and actionable advice for active alerts."""
    if not alerts:
        return {"context": "No active alerts.", "source": "template"}
    alert_text = "; ".join([f"{a['type']}:{a['message']}" for a in alerts[:5]])
    user_prompt = f"Explain these paddy field alerts and give specific management actions: {alert_text}"
    llm_text = _call_openrouter(SYSTEM_PROMPT_BASE, user_prompt, max_tokens=350)
    text = llm_text or _template_alert_context(alerts)
    return {"context": text, "source": "llm" if llm_text else "template"}


def generate_certificate_text(
    farm_profile: Dict,
    credits: Dict,
    verification: Dict,
) -> Dict[str, str]:
    """Generate certificate text for credit retirement."""
    user_prompt = (
        f"Write a formal carbon credit certificate for farmer "
        f"{farm_profile.get('farmer_name')} who earned "
        f"{credits.get('credits_earned', 0):.3f} tCO2e credits at "
        f"{verification.get('level')} verification level."
    )
    llm_text = _call_openrouter(SYSTEM_PROMPT_BASE, user_prompt, max_tokens=400)
    text = llm_text or _template_certificate_text(farm_profile, credits, verification)
    return {"certificate_text": text, "source": "llm" if llm_text else "template"}


def answer_insight_query(
    query: str,
    context: Dict,
) -> Dict[str, str]:
    """Free-form question answering with field context injected."""
    ctx_summary = (
        f"Farm: {context.get('farm_id')}, "
        f"AWD: {context.get('awd_status')}, "
        f"Credits: {context.get('credits_balance', 0):.2f}, "
        f"Score: {context.get('farm_score', 0)}/100"
    )
    user_prompt = f"Field context: {ctx_summary}. Question: {query}"
    llm_text = _call_openrouter(SYSTEM_PROMPT_BASE, user_prompt, max_tokens=400)
    if not llm_text:
        llm_text = (
            f"Based on your field data ({ctx_summary}), I recommend reviewing the AWD schedule "
            f"and ensuring at least 3 dry-down cycles per season to maximise carbon credits."
        )
    return {"answer": llm_text, "source": "llm" if config.OPENROUTER_API_KEY else "template"}
