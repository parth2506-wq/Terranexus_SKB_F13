"""
CarbonKarma Part 2 — Carbon Credit Engine.

Computes carbon credits earned from AWD methane reduction using:
  - IPCC AR6 GWP-100 for CH4 (27.9 × CO2e)
  - Season baseline: conventional flooding (CF) emissions
  - Actual emissions: model-estimated flux
  - Reduction tonnes → credits (1 credit = 1 tonne CO2e)
  - Verification level multiplier (Gold > Silver > Bronze)

Wallet operations:
  - Credit issuance (earn)
  - Credit retirement (burn for certificate)
  - Balance queries
  - Transaction history

Returns:
  {
    credits_earned, total_balance,
    calculation: {baseline_co2e, actual_co2e, reduction_co2e, ...},
    wallet_tx, verification_level
  }
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np

from config import config
from db.store import get_store

# ---------------------------------------------------------------------------
# Credit multipliers by verification level
# ---------------------------------------------------------------------------
_LEVEL_MULTIPLIER = {
    "GOLD":   1.00,
    "SILVER": 0.85,
    "BRONZE": 0.65,
    "FAILED": 0.00,
}

# Minimum reduction % to qualify for any credits
_MIN_REDUCTION_PCT = 5.0


# ---------------------------------------------------------------------------
# Credit calculation
# ---------------------------------------------------------------------------

def calculate_credits(
    methane_aggregate: Dict[str, Any],
    area_ha: float,
    verification_level: str = "SILVER",
    season_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Calculate carbon credits from methane reduction data.

    Parameters
    ----------
    methane_aggregate  : aggregate block from methane_engine
    area_ha            : field area in hectares
    verification_level : "GOLD" | "SILVER" | "BRONZE" | "FAILED"
    season_days        : override if not in aggregate

    Returns
    -------
    calculation dict with all intermediate values + final credits_earned
    """
    sd = season_days or methane_aggregate.get("season_days", 90)
    mean_flux = methane_aggregate.get("mean_daily_flux", 0.0)     # mg CH4/m²/day
    baseline_flux = config.BASELINE_EMISSION_KG_HA * 1e6 / 10_000 / sd  # → mg/m²/day

    # Convert fluxes to kg CH4 / ha / season
    actual_kg_ha = mean_flux * 1e-6 * 10_000 * sd            # mg→kg, m²→ha
    baseline_kg_ha = methane_aggregate.get("baseline_kg_ha", config.BASELINE_EMISSION_KG_HA)
    reduction_kg_ha = max(baseline_kg_ha - actual_kg_ha, 0.0)
    reduction_pct = (reduction_kg_ha / max(baseline_kg_ha, 1e-9)) * 100

    # Total field reduction in tonnes CH4
    total_reduction_t_ch4 = (reduction_kg_ha * area_ha) / 1000.0

    # Convert to CO2e using GWP-100
    reduction_co2e_t = total_reduction_t_ch4 * config.METHANE_GWP_100

    # Baseline and actual in CO2e
    baseline_co2e = (baseline_kg_ha * area_ha / 1000.0) * config.METHANE_GWP_100
    actual_co2e   = baseline_co2e - reduction_co2e_t

    # Apply verification multiplier
    multiplier = _LEVEL_MULTIPLIER.get(verification_level, 0.0)
    credits_earned = max(reduction_co2e_t * multiplier, 0.0) if reduction_pct >= _MIN_REDUCTION_PCT else 0.0

    # USD value
    usd_value = credits_earned * config.CREDIT_PRICE_USD

    return {
        "area_ha": round(area_ha, 4),
        "season_days": sd,
        "baseline_flux_mg_m2_day": round(baseline_flux, 2),
        "actual_flux_mg_m2_day": round(mean_flux, 2),
        "baseline_kg_ha": round(baseline_kg_ha, 2),
        "actual_kg_ha": round(actual_kg_ha, 2),
        "reduction_kg_ha": round(reduction_kg_ha, 2),
        "reduction_pct": round(reduction_pct, 2),
        "total_reduction_t_ch4": round(total_reduction_t_ch4, 4),
        "baseline_co2e_t": round(baseline_co2e, 4),
        "actual_co2e_t": round(actual_co2e, 4),
        "reduction_co2e_t": round(reduction_co2e_t, 4),
        "verification_level": verification_level,
        "verification_multiplier": multiplier,
        "credits_earned": round(credits_earned, 4),
        "usd_value": round(usd_value, 2),
        "gwp_100_ch4": config.METHANE_GWP_100,
        "price_per_credit_usd": config.CREDIT_PRICE_USD,
        "qualifies": reduction_pct >= _MIN_REDUCTION_PCT and verification_level != "FAILED",
    }


# ---------------------------------------------------------------------------
# Wallet operations
# ---------------------------------------------------------------------------

def issue_credits(
    farm_id: str,
    credits_earned: float,
    calculation: Dict,
    verification_result: Dict,
) -> Dict[str, Any]:
    """
    Issue credits to farm wallet and log the transaction.

    Returns wallet transaction dict.
    """
    store = get_store()

    if credits_earned <= 0:
        return {
            "tx_id": None,
            "credits_issued": 0.0,
            "total_balance": store.get_balance(farm_id),
            "reason": "No credits earned (insufficient reduction or verification failed)",
        }

    tx = store.add_wallet_tx(
        farm_id=farm_id,
        tx_type="EARN",
        credits=credits_earned,
        reference=verification_result.get("fingerprint", ""),
        data={
            "calculation": calculation,
            "verification_level": verification_result.get("level"),
            "issued_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    store.log_event(
        farm_id=farm_id,
        event_type="CREDIT_ISSUED",
        description=f"Issued {credits_earned:.4f} credits at {verification_result.get('level')} level",
        data={"tx_id": tx["tx_id"], "credits": credits_earned},
    )

    return {
        "tx_id": tx["tx_id"],
        "credits_issued": credits_earned,
        "total_balance": tx["balance_after"],
    }


def retire_credits(farm_id: str, amount: float, reason: str = "certificate") -> Dict:
    """Retire (burn) credits for certificate issuance."""
    store = get_store()
    balance = store.get_balance(farm_id)
    if amount > balance:
        return {"error": f"Insufficient balance. Have {balance:.4f}, need {amount:.4f}"}
    tx = store.add_wallet_tx(farm_id, "RETIRE", -amount, reference=reason)
    store.log_event(farm_id, "CREDIT_RETIRED", f"Retired {amount:.4f} credits for {reason}")
    return {"tx_id": tx["tx_id"], "retired": amount, "total_balance": tx["balance_after"]}


def get_wallet(farm_id: str) -> Dict:
    """Return current wallet state and transaction history."""
    store = get_store()
    return {
        "farm_id": farm_id,
        "total_balance": store.get_balance(farm_id),
        "transactions": store.get_wallet_history(farm_id, limit=50),
        "currency": "Carbon Credits (CO2e tonnes)",
        "price_per_credit_usd": config.CREDIT_PRICE_USD,
    }


# ---------------------------------------------------------------------------
# Impact metrics (from credits and methane data)
# ---------------------------------------------------------------------------

def compute_impact_metrics(
    calculation: Dict,
    area_ha: float,
    rainfall_records: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Compute broader sustainability impact metrics.

    Returns CO2e reduced, water saved estimate, methane reduction absolute.
    """
    reduction_co2e = calculation.get("reduction_co2e_t", 0.0)
    reduction_pct  = calculation.get("reduction_pct", 0.0)
    season_days    = calculation.get("season_days", 90)

    # Water savings: AWD saves ~25-40 % irrigation water vs CF
    # Approximate: 1,200 mm/season for CF rice, 40 % reduction
    cf_water_mm = 1_200.0
    awd_saving_pct = min(reduction_pct * 0.4, 40.0)  # rough linear coupling
    water_saved_mm = cf_water_mm * (awd_saving_pct / 100.0)
    water_saved_m3_ha = water_saved_mm * 10            # 1 mm = 10 m³/ha
    water_saved_total_m3 = water_saved_m3_ha * area_ha

    # Trees equivalent (1 tree ≈ 21 kg CO2/yr)
    trees_equivalent = int((reduction_co2e * 1000) / 21)

    # Car km equivalent (1 km ≈ 0.12 kg CO2e)
    car_km_equivalent = int((reduction_co2e * 1000) / 0.12)

    return {
        "co2e_reduced_tonnes": round(reduction_co2e, 4),
        "ch4_reduced_kg_ha": round(calculation.get("reduction_kg_ha", 0), 2),
        "ch4_reduction_pct": round(reduction_pct, 2),
        "water_saved_mm": round(water_saved_mm, 1),
        "water_saved_m3_total": round(water_saved_total_m3, 1),
        "water_saving_pct": round(awd_saving_pct, 1),
        "trees_equivalent": trees_equivalent,
        "car_km_equivalent": car_km_equivalent,
        "area_ha": area_ha,
        "season_days": season_days,
    }
