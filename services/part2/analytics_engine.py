"""
CarbonKarma Part 2 — Advanced Analytics Engine.

Implements all 8 analytics modules:
  1. Farm Score        — overall_score, water_efficiency, methane_control, awd_compliance
  2. Comparative       — your vs regional methane benchmarks
  3. Historical Trends — 7/30/90 day rolling statistics
  4. Alerts/Insights   — flood alerts, methane warnings, recommendations
  5. Predictions       — 7-day rainfall/methane/irrigation forecast
  6. Field Segmentation— zone-wise methane from pixel fusion
  7. Impact Metrics    — CO2 reduced, water saved (delegates to credit_engine)
  8. Farm Profile      — static metadata from env / store
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import config
from db.store import get_store


# ---------------------------------------------------------------------------
# 1. FARM SCORE
# ---------------------------------------------------------------------------

def compute_farm_score(
    fusion_data: List[Dict],
    awd_result: Dict,
    methane_aggregate: Dict,
    verification_confidence: float,
) -> Dict[str, Any]:
    """Overall farm sustainability score (0–100) across four dimensions."""

    # Water efficiency: reward moderate water levels (AWD range 0.3–0.7)
    water_levels = [r.get("water_level", 0.5) for r in fusion_data]
    awd_zone = [0.3 <= w <= 0.7 for w in water_levels]
    water_efficiency = round(float(np.mean(awd_zone)) * 100, 1)

    # Methane control: inverse of normalised mean flux
    mean_flux = methane_aggregate.get("mean_daily_flux", 300.0)
    methane_score = round(max(0, 1.0 - (mean_flux / 600.0)) * 100, 1)

    # AWD compliance: based on cycles and LSTM signal
    cycles = awd_result.get("cycles", 0)
    lstm   = awd_result.get("lstm_signal", 0.0)
    awd_compliance = round(min((cycles / 4.0 * 0.5 + lstm * 0.5) * 100, 100), 1)

    # Verification quality
    verif_score = round(verification_confidence * 100, 1)

    # Weighted overall
    overall = round(
        water_efficiency * 0.25 +
        methane_score    * 0.30 +
        awd_compliance   * 0.30 +
        verif_score      * 0.15,
        1
    )

    # Grade
    grade = "A" if overall >= 80 else "B" if overall >= 65 else "C" if overall >= 50 else "D"

    return {
        "overall_score": overall,
        "grade": grade,
        "water_efficiency": water_efficiency,
        "methane_control": methane_score,
        "awd_compliance": awd_compliance,
        "verification_quality": verif_score,
        "max_score": 100,
    }


# ---------------------------------------------------------------------------
# 2. COMPARATIVE ANALYSIS
# ---------------------------------------------------------------------------

# Regional benchmarks for tropical paddy (Southeast Asia / South Asia)
_REGIONAL_BENCHMARKS = {
    "south_asia": {"mean_flux": 320.0, "std": 85.0, "label": "South Asia"},
    "southeast_asia": {"mean_flux": 350.0, "std": 95.0, "label": "Southeast Asia"},
    "global_cf": {"mean_flux": 400.0, "std": 100.0, "label": "Global CF Baseline"},
}


def comparative_analysis(
    methane_aggregate: Dict,
    awd_result: Dict,
    region: str = "south_asia",
) -> Dict[str, Any]:
    your_flux  = methane_aggregate.get("mean_daily_flux", 300.0)
    bench      = _REGIONAL_BENCHMARKS.get(region, _REGIONAL_BENCHMARKS["south_asia"])
    reg_flux   = bench["mean_flux"]
    reg_std    = bench["std"]

    pct_vs_regional = round((your_flux - reg_flux) / reg_flux * 100, 2)
    z_score = round((your_flux - reg_flux) / max(reg_std, 1e-9), 3)

    # Percentile approximation from z-score (normal dist)
    from math import erf, sqrt
    percentile = round((1 + erf(z_score / sqrt(2))) / 2 * 100, 1)

    performance = (
        "top_quartile"    if percentile <= 25 else
        "above_average"   if percentile <= 50 else
        "below_average"   if percentile <= 75 else
        "bottom_quartile"
    )

    return {
        "your_flux_mg_m2_day": round(your_flux, 2),
        "regional_mean_mg_m2_day": reg_flux,
        "regional_std": reg_std,
        "region_label": bench["label"],
        "pct_vs_regional": pct_vs_regional,
        "z_score": z_score,
        "percentile": percentile,
        "performance": performance,
        "all_benchmarks": {
            k: {"mean": v["mean_flux"], "label": v["label"]}
            for k, v in _REGIONAL_BENCHMARKS.items()
        },
    }


# ---------------------------------------------------------------------------
# 3. HISTORICAL TRENDS
# ---------------------------------------------------------------------------

def historical_trends(
    farm_id: str,
    fusion_data: List[Dict],
    windows: List[int] = [7, 30, 90],
) -> Dict[str, Any]:
    """
    Compute rolling statistics over 7/30/90-day windows from stored history
    and current fusion data.
    """
    store = get_store()
    history = store.get_history(farm_id, limit=100)

    # Merge history with current fusion (deduplicate by timestamp)
    all_records: Dict[str, Dict] = {}
    for r in history:
        all_records[r["timestamp"]] = r
    for r in fusion_data:
        all_records[str(r.get("timestamp", ""))] = r
    sorted_records = sorted(all_records.values(), key=lambda x: x.get("timestamp", ""))

    now = date.today()
    trends = {}

    for w in windows:
        cutoff = (now - timedelta(days=w)).isoformat()
        window_recs = [r for r in sorted_records if str(r.get("timestamp", "")) >= cutoff]

        if not window_recs:
            trends[f"{w}d"] = {"n": 0, "note": "No data in window"}
            continue

        def _safe_mean(key):
            vals = [r[key] for r in window_recs if key in r and r[key] is not None]
            return round(float(np.mean(vals)), 4) if vals else None

        def _safe_trend(key):
            vals = [r[key] for r in window_recs if key in r and r[key] is not None]
            if len(vals) < 2:
                return "insufficient_data"
            slope = float(np.polyfit(range(len(vals)), vals, 1)[0])
            if slope > 0.005: return "rising"
            if slope < -0.005: return "falling"
            return "stable"

        trends[f"{w}d"] = {
            "n_observations": len(window_recs),
            "water_level":    {"mean": _safe_mean("water_level"),    "trend": _safe_trend("water_level")},
            "ndvi":           {"mean": _safe_mean("ndvi"),            "trend": _safe_trend("ndvi")},
            "temperature":    {"mean": _safe_mean("temperature"),     "trend": _safe_trend("temperature")},
            "rainfall":       {"mean": _safe_mean("rainfall"),        "trend": _safe_trend("rainfall")},
            "soil_moisture":  {"mean": _safe_mean("soil_moisture"),   "trend": _safe_trend("soil_moisture")},
        }

    return {"windows": trends, "total_records": len(sorted_records)}


# ---------------------------------------------------------------------------
# 4. ALERTS AND INSIGHTS
# ---------------------------------------------------------------------------

def generate_alerts(
    fusion_data: List[Dict],
    awd_result: Dict,
    methane_steps: List[Dict],
    farm_score: Dict,
) -> Dict[str, Any]:
    alerts = []
    recommendations = []
    insights = []

    latest = fusion_data[-1] if fusion_data else {}
    water_level = latest.get("water_level", 0.5)
    ndvi = latest.get("ndvi", 0.4)
    temp = latest.get("temperature", 28.0)
    rainfall = latest.get("rainfall", 0.0)

    # ── Flooding alert ────────────────────────────────────────────────────
    if water_level > 0.90:
        alerts.append({
            "type": "FLOOD_ALERT",
            "severity": "HIGH",
            "message": f"Field water level critically high ({water_level:.0%}). Risk of uncontrolled flooding.",
            "timestamp": latest.get("timestamp"),
        })
        recommendations.append("Open drainage outlets immediately to prevent crop damage.")

    elif water_level > 0.75:
        alerts.append({
            "type": "HIGH_WATER",
            "severity": "MEDIUM",
            "message": f"Water level elevated ({water_level:.0%}). Monitor closely.",
            "timestamp": latest.get("timestamp"),
        })

    # ── Drought / over-drying alert ───────────────────────────────────────
    if water_level < 0.10 and ndvi > 0.3:
        alerts.append({
            "type": "DRY_ALERT",
            "severity": "HIGH",
            "message": f"Field critically dry ({water_level:.0%}) during active crop growth. Risk of crop stress.",
            "timestamp": latest.get("timestamp"),
        })
        recommendations.append("Initiate irrigation within 24 hours to prevent yield loss.")

    # ── Methane warning ───────────────────────────────────────────────────
    if methane_steps:
        recent_high = [s for s in methane_steps[-3:] if s.get("category") == "high"]
        if len(recent_high) >= 2:
            alerts.append({
                "type": "METHANE_WARNING",
                "severity": "HIGH",
                "message": f"High CH₄ emissions detected in last 3 observations ({len(recent_high)}/3 steps). Credits at risk.",
                "timestamp": methane_steps[-1].get("timestamp"),
            })
            recommendations.append("Initiate drying cycle immediately to reduce anaerobic conditions.")

    # ── AWD compliance alert ──────────────────────────────────────────────
    awd_compliance = farm_score.get("awd_compliance", 0)
    if awd_compliance < 40:
        alerts.append({
            "type": "AWD_COMPLIANCE",
            "severity": "MEDIUM",
            "message": f"AWD compliance score low ({awd_compliance:.0f}/100). Fewer cycles detected than required.",
            "timestamp": latest.get("timestamp"),
        })
        recommendations.append("Enforce dry-down periods of at least 5 days between irrigations.")

    # ── Temperature heat stress ───────────────────────────────────────────
    if temp > 38.0:
        alerts.append({
            "type": "HEAT_STRESS",
            "severity": "MEDIUM",
            "message": f"Temperature {temp:.1f}°C approaching crop heat stress threshold.",
            "timestamp": latest.get("timestamp"),
        })

    # ── Positive insights ─────────────────────────────────────────────────
    if awd_result.get("cycles", 0) >= 3:
        insights.append({
            "type": "GOOD_AWD_PRACTICE",
            "message": f"Excellent AWD implementation — {awd_result['cycles']} cycles detected this season.",
        })
    if farm_score.get("overall_score", 0) >= 75:
        insights.append({
            "type": "HIGH_FARM_SCORE",
            "message": f"Farm score {farm_score['overall_score']}/100 (Grade {farm_score['grade']}) — eligible for Gold verification.",
        })
    if ndvi > 0.65:
        insights.append({
            "type": "GOOD_CROP_HEALTH",
            "message": f"Strong vegetation index (NDVI={ndvi:.2f}) indicates healthy crop growth.",
        })

    if not recommendations:
        recommendations.append("Continue current AWD schedule. No immediate actions required.")

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "high_severity_count": sum(1 for a in alerts if a["severity"] == "HIGH"),
        "insights": insights,
        "recommendations": recommendations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 5. PREDICTIONS (7-day)
# ---------------------------------------------------------------------------

def generate_predictions(
    fusion_data: List[Dict],
    weather_records: List[Dict],
    methane_steps: List[Dict],
) -> Dict[str, Any]:
    """
    Generate 7-day ahead forecasts using exponential smoothing + physics rules.
    """
    today = date.today()

    # Fit simple exponential smoothing to recent series
    def _ema_forecast(series: List[float], alpha: float, n_ahead: int) -> List[float]:
        if not series:
            return [0.0] * n_ahead
        s = series[0]
        for v in series[1:]:
            s = alpha * v + (1 - alpha) * s
        # Flat forward forecast with slight mean-reversion
        long_mean = float(np.mean(series))
        preds = []
        cur = s
        for _ in range(n_ahead):
            cur = alpha * long_mean + (1 - alpha) * cur + np.random.normal(0, 0.02 * abs(cur))
            preds.append(float(np.clip(cur, 0, None)))
        return preds

    rainfall_series = [r.get("rainfall", 0.0) for r in weather_records]
    water_series    = [r.get("water_level", 0.5) for r in fusion_data]
    methane_series  = [s.get("methane", 250.0) for s in methane_steps]

    rain_forecast    = _ema_forecast(rainfall_series, 0.35, 7)
    water_forecast   = _ema_forecast(water_series, 0.25, 7)
    methane_forecast = _ema_forecast(methane_series, 0.30, 7)

    forecast_dates = [(today + timedelta(days=i+1)).isoformat() for i in range(7)]

    # Irrigation advice: recommend irrigation when forecast water < 0.25
    irrigation_advice = []
    for i, (d, wf, rf) in enumerate(zip(forecast_dates, water_forecast, rain_forecast)):
        if wf < 0.25 and rf < 5.0:
            irrigation_advice.append({
                "date": d,
                "action": "IRRIGATE",
                "reason": f"Forecast water level {wf:.2f} with {rf:.1f}mm rain expected",
                "urgency": "HIGH" if wf < 0.15 else "MEDIUM",
            })
        elif wf > 0.80:
            irrigation_advice.append({
                "date": d,
                "action": "DRAIN",
                "reason": f"Forecast water level high ({wf:.2f}). Open drainage.",
                "urgency": "MEDIUM",
            })

    daily_forecasts = [
        {
            "date": d,
            "rainfall_mm": round(rain_forecast[i], 2),
            "water_level": round(min(water_forecast[i], 1.0), 3),
            "methane_mg_m2_day": round(methane_forecast[i], 1),
            "methane_category": (
                "low" if methane_forecast[i] < config.METHANE_LOW_THRESHOLD else
                "high" if methane_forecast[i] > config.METHANE_HIGH_THRESHOLD else
                "medium"
            ),
        }
        for i, d in enumerate(forecast_dates)
    ]

    return {
        "forecast_horizon_days": 7,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "daily_forecasts": daily_forecasts,
        "irrigation_advice": irrigation_advice,
        "summary": {
            "total_rain_forecast_mm": round(sum(rain_forecast), 1),
            "avg_water_level": round(float(np.mean(water_forecast)), 3),
            "avg_methane_forecast": round(float(np.mean(methane_forecast)), 1),
            "irrigation_events_needed": sum(1 for a in irrigation_advice if a["action"] == "IRRIGATE"),
        },
    }


# ---------------------------------------------------------------------------
# 6. FIELD SEGMENTATION (zone-wise methane)
# ---------------------------------------------------------------------------

def field_segmentation(
    pixel_fusion: Dict[str, Any],
    lat: float,
    lon: float,
    bbox: List[float],
    patch_size: int = 16,
) -> Dict[str, Any]:
    """
    Divide the field into a grid of zones and compute zone-level statistics.
    Returns N×N zone grid with methane proxy, water level, and NDVI per zone.
    Patch_size is downsampled to 4×4 or 8×8 for tractable zone count.
    """
    import cv2

    zone_size = min(patch_size, 8)   # max 8×8 zones for readability

    water_arr = pixel_fusion.get("water_prob", np.full((patch_size, patch_size), 0.5))
    ndvi_arr  = pixel_fusion.get("ndvi",       np.full((patch_size, patch_size), 0.4))
    lst_arr   = pixel_fusion.get("lst_norm",   np.full((patch_size, patch_size), 0.5))
    soil_arr  = pixel_fusion.get("soil_moisture", np.full((patch_size, patch_size), 0.4))

    def _pool(arr):
        return cv2.resize(arr.astype(np.float32), (zone_size, zone_size), interpolation=cv2.INTER_AREA)

    w = _pool(water_arr); n = _pool(ndvi_arr)
    l = _pool(lst_arr);   s = _pool(soil_arr)

    # Methane proxy: physics formula (mirrors methane_engine fallback)
    ch4_proxy = np.clip(
        w * 0.40 + n * 0.25 + l * 0.15 + s * 0.10,
        0.0, 1.0
    ) * 600 + 50   # scale to realistic range

    min_lon, min_lat, max_lon, max_lat = bbox

    zones = []
    for row in range(zone_size):
        for col in range(zone_size):
            z_lat = max_lat - (row + 0.5) / zone_size * (max_lat - min_lat)
            z_lon = min_lon + (col + 0.5) / zone_size * (max_lon - min_lon)
            flux = float(ch4_proxy[row, col])
            cat = "low" if flux < config.METHANE_LOW_THRESHOLD else (
                "high" if flux > config.METHANE_HIGH_THRESHOLD else "medium")
            zones.append({
                "zone_id": f"Z{row:02d}{col:02d}",
                "row": row, "col": col,
                "lat": round(z_lat, 6), "lon": round(z_lon, 6),
                "methane_proxy": round(flux, 1),
                "methane_category": cat,
                "water_level": round(float(w[row, col]), 3),
                "ndvi": round(float(n[row, col]), 3),
                "soil_moisture": round(float(s[row, col]), 3),
            })

    hotspot = max(zones, key=lambda z: z["methane_proxy"])
    coldspot = min(zones, key=lambda z: z["methane_proxy"])

    return {
        "grid_size": f"{zone_size}x{zone_size}",
        "n_zones": len(zones),
        "zones": zones,
        "hotspot_zone": hotspot["zone_id"],
        "coldspot_zone": coldspot["zone_id"],
        "mean_methane_proxy": round(float(np.mean([z["methane_proxy"] for z in zones])), 1),
        "max_methane_proxy": round(float(hotspot["methane_proxy"]), 1),
    }


# ---------------------------------------------------------------------------
# 8. FARM PROFILE
# ---------------------------------------------------------------------------

def get_farm_profile(farm_id: str) -> Dict[str, Any]:
    """Load farm profile from store or build from environment defaults."""
    store = get_store()
    profile = store.get_farm_profile(farm_id)
    if profile:
        return profile

    # Build from environment defaults
    profile = {
        "farm_id": farm_id,
        "farmer_name": os.getenv("FARMER_NAME", "Ravi Kumar"),
        "farm_location": os.getenv("FARM_LOCATION", "Thanjavur, Tamil Nadu, India"),
        "farm_area_ha": float(os.getenv("FARM_AREA_HA", "4.5")),
        "crop_type": os.getenv("CROP_TYPE", "IR64 Paddy"),
        "season": os.getenv("SEASON", "Kharif 2025"),
        "coordinates": {
            "lat": float(os.getenv("FARM_LAT", "10.7867")),
            "lon": float(os.getenv("FARM_LON", "79.1378")),
        },
        "irrigation_source": os.getenv("IRRIGATION_SOURCE", "Canal + Groundwater"),
        "soil_type": os.getenv("SOIL_TYPE", "Clay loam"),
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "program": "CarbonKarma dMRV v1.0",
    }
    store.upsert_farm_profile(farm_id, profile)
    return profile


# ---------------------------------------------------------------------------
# 9. AUDIT TRAIL
# ---------------------------------------------------------------------------

def get_audit_trail(farm_id: str, limit: int = 50) -> Dict[str, Any]:
    store = get_store()
    events = store.get_audit_trail(farm_id, limit=limit)
    return {
        "farm_id": farm_id,
        "total_events": len(events),
        "events": events,
    }
