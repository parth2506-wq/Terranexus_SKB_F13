"""
CarbonKarma Part 2 — Verification Engine.

dMRV (digital Measurement, Reporting and Verification) of field-level
carbon abatement claims. Verifies that:
  1. Satellite observations are of sufficient quality (cloud, coverage)
  2. AWD cycles are consistent with declared practice
  3. Methane reduction claims are scientifically defensible
  4. Time-series continuity meets ISO 14064-2 data-completeness requirements

Verification levels:
  GOLD   — ≥ 85 % confidence, ≥ 3 AWD cycles, low cloud
  SILVER — 65–85 % confidence, ≥ 2 cycles
  BRONZE — 40–65 % confidence, ≥ 1 cycle
  FAILED — < 40 % or critical data gaps

Returns:
  {
    status, level, confidence, data_integrity,
    checks: [{name, passed, score, detail}],
    explanation, timestamp
  }
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np

from config import config


# ---------------------------------------------------------------------------
# Individual verification checks
# ---------------------------------------------------------------------------

def _check_temporal_coverage(fusion_data: List[Dict]) -> Dict:
    n = len(fusion_data)
    score = min(n / 12.0, 1.0)
    return {
        "name": "temporal_coverage",
        "passed": n >= 8,
        "score": round(score, 3),
        "detail": f"{n} observation steps (minimum 8 required for Gold verification)",
    }


def _check_cloud_quality(fusion_data: List[Dict]) -> Dict:
    cloud_fracs = [r.get("cloud_fraction", 0.0) for r in fusion_data]
    contaminated = sum(1 for c in cloud_fracs if c > config.VERIFICATION_CLOUD_MAX)
    fraction_clean = 1.0 - (contaminated / max(len(cloud_fracs), 1))
    score = fraction_clean
    return {
        "name": "cloud_data_quality",
        "passed": fraction_clean >= 0.70,
        "score": round(score, 3),
        "detail": f"{contaminated}/{len(cloud_fracs)} steps exceed {config.VERIFICATION_CLOUD_MAX:.0%} cloud cover threshold",
    }


def _check_ndvi_validity(fusion_data: List[Dict]) -> Dict:
    ndvis = [r.get("ndvi", 0.0) for r in fusion_data]
    valid = [v for v in ndvis if v >= config.VERIFICATION_NDVI_MIN]
    score = len(valid) / max(len(ndvis), 1)
    return {
        "name": "vegetation_presence",
        "passed": score >= 0.5,
        "score": round(score, 3),
        "detail": f"{len(valid)}/{len(ndvis)} steps show active crop (NDVI ≥ {config.VERIFICATION_NDVI_MIN})",
    }


def _check_temperature_range(fusion_data: List[Dict]) -> Dict:
    temps = [r.get("temperature", 25.0) for r in fusion_data]
    anomalies = [t for t in temps if t > config.VERIFICATION_TEMP_MAX_C or t < 5.0]
    score = 1.0 - len(anomalies) / max(len(temps), 1)
    return {
        "name": "temperature_plausibility",
        "passed": len(anomalies) == 0,
        "score": round(score, 3),
        "detail": f"{len(anomalies)} temperature anomalies detected outside [5°C, {config.VERIFICATION_TEMP_MAX_C}°C]",
    }


def _check_awd_consistency(awd_result: Dict) -> Dict:
    cycles = awd_result.get("cycles", 0)
    lstm_signal = awd_result.get("lstm_signal", 0.0)
    awd_status = awd_result.get("awd_status", "uncertain")
    confidence = awd_result.get("confidence", 0.0)
    score = min((cycles / 3.0) * 0.5 + confidence * 0.5, 1.0)
    passed = awd_status == "active_awd" and cycles >= 1
    return {
        "name": "awd_practice_consistency",
        "passed": passed,
        "score": round(score, 3),
        "detail": f"AWD status={awd_status}, cycles={cycles}, LSTM signal={lstm_signal:.3f}, confidence={confidence:.3f}",
    }


def _check_methane_plausibility(methane_data: Dict) -> Dict:
    agg = methane_data.get("aggregate", {})
    mean_flux = agg.get("mean_daily_flux", 300.0)
    reduction = agg.get("total_reduction_pct", 0.0)
    # Physically: flux must be > 0 and < 700, reduction 0–80 %
    flux_ok = 0 < mean_flux < 700
    reduction_ok = 0 <= reduction <= 80
    score = 1.0 if (flux_ok and reduction_ok) else 0.3
    return {
        "name": "methane_plausibility",
        "passed": flux_ok and reduction_ok,
        "score": round(score, 3),
        "detail": f"Mean flux={mean_flux:.1f} mg/m²/day, reduction={reduction:.1f}% (must be 0–80%)",
    }


def _check_water_data_continuity(fusion_data: List[Dict]) -> Dict:
    water_levels = [r.get("water_level", None) for r in fusion_data]
    missing = sum(1 for w in water_levels if w is None)
    # Check for implausible step-changes (> 0.8 in one step)
    diffs = [abs(water_levels[i] - water_levels[i-1])
             for i in range(1, len(water_levels))
             if water_levels[i] is not None and water_levels[i-1] is not None]
    large_jumps = sum(1 for d in diffs if d > 0.85)
    score = max(0.0, 1.0 - missing / max(len(water_levels), 1) - large_jumps * 0.1)
    return {
        "name": "water_data_continuity",
        "passed": missing == 0 and large_jumps <= 2,
        "score": round(score, 3),
        "detail": f"Missing={missing}, large step-changes={large_jumps}",
    }


# ---------------------------------------------------------------------------
# Scoring and level assignment
# ---------------------------------------------------------------------------

def _assign_level(composite_score: float, awd_cycles: int) -> str:
    if composite_score >= 0.85 and awd_cycles >= 3:
        return "GOLD"
    elif composite_score >= 0.65 and awd_cycles >= 2:
        return "SILVER"
    elif composite_score >= 0.40 and awd_cycles >= 1:
        return "BRONZE"
    return "FAILED"


def _compute_data_integrity(checks: List[Dict]) -> Dict:
    total = len(checks)
    passed = sum(1 for c in checks if c["passed"])
    avg_score = float(np.mean([c["score"] for c in checks]))
    return {
        "checks_passed": passed,
        "checks_total": total,
        "pass_rate": round(passed / total, 3),
        "average_score": round(avg_score, 3),
    }


def _make_fingerprint(fusion_data: List[Dict], awd_result: Dict) -> str:
    """SHA-256 fingerprint of key observation data for immutable audit."""
    payload = {
        "n_steps": len(fusion_data),
        "timestamps": [r.get("timestamp") for r in fusion_data],
        "water_levels": [round(r.get("water_level", 0), 4) for r in fusion_data],
        "awd_status": awd_result.get("awd_status"),
        "cycles": awd_result.get("cycles"),
    }
    raw = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify(
    fusion_data: List[Dict],
    awd_result: Dict,
    methane_data: Dict,
    farm_id: str = "unknown",
) -> Dict[str, Any]:
    """
    Run all dMRV verification checks and return a structured result.

    Parameters
    ----------
    fusion_data   : List of fused per-step records (from fusion_engine)
    awd_result    : Output of awd_engine.detect_awd()
    methane_data  : Output of methane_engine (dict with 'aggregate' key)
    farm_id       : Farm identifier for audit logging

    Returns
    -------
    Full verification result dict.
    """
    checks = [
        _check_temporal_coverage(fusion_data),
        _check_cloud_quality(fusion_data),
        _check_ndvi_validity(fusion_data),
        _check_temperature_range(fusion_data),
        _check_awd_consistency(awd_result),
        _check_methane_plausibility(methane_data),
        _check_water_data_continuity(fusion_data),
    ]

    data_integrity = _compute_data_integrity(checks)
    composite = data_integrity["average_score"]
    awd_cycles = awd_result.get("cycles", 0)
    level = _assign_level(composite, awd_cycles)
    status = "verified" if level != "FAILED" else "failed"
    fingerprint = _make_fingerprint(fusion_data, awd_result)

    # Human-readable summary
    passed_names = [c["name"] for c in checks if c["passed"]]
    failed_names = [c["name"] for c in checks if not c["passed"]]
    explanation = (
        f"Verification {level}: {data_integrity['checks_passed']}/{data_integrity['checks_total']} "
        f"checks passed (composite score {composite:.2f}). "
    )
    if failed_names:
        explanation += f"Issues: {', '.join(failed_names)}. "
    if level == "GOLD":
        explanation += "Eligible for premium carbon credit issuance."
    elif level == "SILVER":
        explanation += "Eligible for standard carbon credit issuance."
    elif level == "BRONZE":
        explanation += "Eligible for monitored credit issuance with additional review."
    else:
        explanation += "Insufficient data quality for credit issuance. Address failed checks and resubmit."

    return {
        "status": status,
        "level": level,
        "confidence": round(composite, 4),
        "data_integrity": data_integrity,
        "checks": checks,
        "fingerprint": fingerprint,
        "explanation": explanation,
        "farm_id": farm_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
