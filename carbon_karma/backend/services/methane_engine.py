"""
CarbonKarma — Methane Estimation Engine.

Orchestrates the MethaneEstimator model with fused field data to produce
per-timestep and season-aggregate CH4 flux estimates.

Baseline for reduction calculation:
  Conventional continuously flooded paddy (CF) emits approximately
  400 mg CH4 / m2 / day on average in tropical Asia (IPCC Tier 1).
  AWD reduces this by 30-70 % depending on drying intensity and duration.

Per-timestep output:
  { methane, category, reduction_percent }

Season-aggregate output:
  {
    season_total_kg_ha   : kg CH4 / ha over the observation period
    mean_daily_flux      : mg CH4 / m2 / day
    max_daily_flux       : peak value
    baseline_kg_ha       : CF baseline for same period
    total_reduction_pct  : weighted average reduction %
  }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from config import config
from models.methane_model import MethaneEstimator, build_methane_model, run_methane_model

logger = logging.getLogger(__name__)

# Conventional flooded paddy CF baseline (mg CH4 / m2 / day) — IPCC Tier 1
CF_BASELINE_FLUX = 400.0
# 1 mg/m2/day × (season days) × 10,000 m2/ha ÷ 1e6 mg/kg → kg/ha
_MG_M2_DAY_TO_KG_HA_DAY = 10_000 / 1_000_000  # = 0.01


# ---------------------------------------------------------------------------
# Per-timestep estimation
# ---------------------------------------------------------------------------

def estimate_methane_per_step(
    fused_records: List[Dict[str, Any]],
    methane_model: Optional[MethaneEstimator] = None,
    device: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Run the MethaneEstimator for every time step in fused_records.

    Parameters
    ----------
    fused_records   : Output of fusion_engine.run_fusion() (possibly AWD-annotated)
    methane_model   : Pre-built MethaneEstimator (built if None)
    device          : Torch device

    Returns
    -------
    List of per-step methane dicts:
        timestamp, methane, category, reduction_percent
    """
    device = device or config.MODEL_DEVICE

    if methane_model is None:
        methane_model = build_methane_model(device=device)

    results: List[Dict[str, Any]] = []

    for rec in fused_records:
        try:
            out = run_methane_model(
                model=methane_model,
                cnn_feature_vector=rec["cnn_feature_vector"],
                lstm_hidden_vector=[0.0] * config.LSTM_HIDDEN_SIZE,  # step-level default
                ndvi_mean=rec["ndvi_mean"],
                lst_celsius_norm=rec["lst_celsius_norm"],
                rainfall_norm=rec["rainfall_norm"],
                soil_moisture_mean=rec["soil_moisture_mean"],
                device=device,
            )
        except Exception as exc:
            logger.warning("Methane model failed at %s: %s — using physics fallback.", rec["timestamp"], exc)
            out = _physics_fallback(rec)

        results.append({
            "timestamp": rec["timestamp"],
            **out,
        })

    return results


def _physics_fallback(rec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple physics-based fallback when the neural model errors.

    Methane flux is highest when:
      - Field is flooded (water_level high)
      - NDVI high (organic substrate)
      - Temperature high
      - Rainfall adds episodic anaerobic pulses
    """
    water_w = rec.get("water_level", 0.5)
    ndvi_w = rec.get("ndvi_mean", 0.4)
    temp_w = rec.get("lst_celsius_norm", 0.5)
    rain_w = min(rec.get("rainfall_norm", 0.0) * 0.5, 0.3)

    raw = (water_w * 0.45 + ndvi_w * 0.25 + temp_w * 0.20 + rain_w * 0.10)
    flux = float(np.clip(raw * CF_BASELINE_FLUX + 50, 50, 600))

    awd = rec.get("awd_status", "conventional")
    reduction = 0.0 if awd == "conventional" else float(np.clip((1.0 - water_w) * 60.0, 0, 75))

    category = (
        "low" if flux < config.METHANE_LOW_THRESHOLD else
        "high" if flux > config.METHANE_HIGH_THRESHOLD else
        "medium"
    )

    return {
        "methane": round(flux, 2),
        "category": category,
        "reduction_percent": round(reduction, 2),
    }


# ---------------------------------------------------------------------------
# Season aggregate
# ---------------------------------------------------------------------------

def compute_season_aggregate(
    per_step_results: List[Dict[str, Any]],
    step_days: int = 10,
) -> Dict[str, Any]:
    """
    Aggregate per-step methane flux into season-level statistics.

    Parameters
    ----------
    per_step_results : Output of estimate_methane_per_step()
    step_days        : Days represented by each observation step

    Returns
    -------
    Season-level aggregate dict.
    """
    if not per_step_results:
        return {}

    fluxes = [r["methane"] for r in per_step_results]
    reductions = [r["reduction_percent"] for r in per_step_results]
    n_steps = len(fluxes)
    season_days = n_steps * step_days

    mean_flux = float(np.mean(fluxes))
    max_flux = float(np.max(fluxes))

    # Convert mg/m2/day → kg/ha over season_days
    season_total_kg_ha = mean_flux * _MG_M2_DAY_TO_KG_HA_DAY * season_days
    baseline_kg_ha = CF_BASELINE_FLUX * _MG_M2_DAY_TO_KG_HA_DAY * season_days
    total_reduction_pct = float(np.mean(reductions))

    # Category distribution
    categories = [r["category"] for r in per_step_results]
    cat_dist = {
        "low": categories.count("low"),
        "medium": categories.count("medium"),
        "high": categories.count("high"),
    }

    return {
        "season_days": season_days,
        "n_observations": n_steps,
        "mean_daily_flux": round(mean_flux, 2),
        "max_daily_flux": round(max_flux, 2),
        "season_total_kg_ha": round(season_total_kg_ha, 2),
        "baseline_kg_ha": round(baseline_kg_ha, 2),
        "total_reduction_pct": round(total_reduction_pct, 2),
        "category_distribution": cat_dist,
        "cf_baseline_flux": CF_BASELINE_FLUX,
    }
