"""
CarbonKarma — Weather data ingestion via Open-Meteo API.

Fetches or simulates daily rainfall (mm) and 2-m air temperature (°C) for
each time step. Open-Meteo is free and requires no API key.

Live endpoint (ERA5-Land archive):
  https://archive-api.open-meteo.com/v1/era5

Falls back to realistic mock data when:
  - USE_MOCK_WEATHER=true in .env, or
  - the network request fails
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import requests

from config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock data generator
# ---------------------------------------------------------------------------

def _mock_weather(
    timestamps: List[str],
    lat: float,
    lon: float,
) -> List[Dict[str, Any]]:
    """
    Generate realistic paddy-region weather data (tropical monsoon regime).

    Monsoon season (Jun-Sep): heavy rainfall, modestly warm.
    Dry season (Nov-Feb): near-zero rainfall, cooler nights.
    """
    records = []
    np.random.seed(abs(int(lat * 100 + lon * 100)) % 10_000)

    for ts in timestamps:
        d = date.fromisoformat(ts)
        month = d.month

        # Seasonal rainfall distribution (mm/day)
        if month in (6, 7, 8, 9):          # Monsoon
            base_rain = np.random.exponential(scale=8.0)
        elif month in (10, 5):              # Transition
            base_rain = np.random.exponential(scale=3.0)
        elif month in (11, 12, 1, 2):      # Dry
            base_rain = np.random.exponential(scale=0.5) * (np.random.random() < 0.15)
        else:                               # Mar-Apr (pre-monsoon)
            base_rain = np.random.exponential(scale=2.0)

        rainfall_mm = round(float(np.clip(base_rain, 0, 80)), 2)

        # Temperature: tropical range ~22-36 °C with seasonal modulation
        seasonal_offset = 4.0 * np.sin(2 * np.pi * (month - 4) / 12)
        temp_c = 29.0 + seasonal_offset + np.random.normal(0, 1.5)
        temp_c = round(float(np.clip(temp_c, 18.0, 40.0)), 2)

        records.append({
            "timestamp": ts,
            "rainfall_mm": rainfall_mm,
            "temperature_c": temp_c,
            "source": "mock",
        })

    return records


# ---------------------------------------------------------------------------
# Live Open-Meteo fetcher
# ---------------------------------------------------------------------------

def _fetch_open_meteo(
    lat: float,
    lon: float,
    timestamps: List[str],
) -> Optional[List[Dict[str, Any]]]:
    """
    Attempt to fetch historical daily weather from Open-Meteo ERA5-Land.
    Returns None on failure.
    """
    dates = sorted(timestamps)
    start_date = dates[0]
    end_date = dates[-1]

    url = "https://archive-api.open-meteo.com/v1/era5"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,temperature_2m_mean",
        "timezone": "auto",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        daily = data.get("daily", {})
        api_dates = daily.get("time", [])
        precip = daily.get("precipitation_sum", [])
        temp = daily.get("temperature_2m_mean", [])

        # Build a date → (rain, temp) lookup
        lookup: Dict[str, tuple] = {}
        for i, d in enumerate(api_dates):
            lookup[d] = (
                float(precip[i]) if precip[i] is not None else 0.0,
                float(temp[i])   if temp[i]   is not None else 28.0,
            )

        records = []
        for ts in timestamps:
            rain_val, temp_val = lookup.get(ts, (0.0, 28.0))
            records.append({
                "timestamp": ts,
                "rainfall_mm": round(rain_val, 2),
                "temperature_c": round(temp_val, 2),
                "source": "open-meteo",
            })
        return records

    except Exception as exc:
        logger.warning("Open-Meteo request failed (%s) — using mock weather.", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_weather(
    lat: float,
    lon: float,
    timestamps: List[str],
) -> List[Dict[str, Any]]:
    """
    Return per-timestamp weather records for a location.

    Uses live Open-Meteo ERA5 archive if USE_MOCK_WEATHER=false, otherwise
    (or on network failure) falls back to the physics-informed mock generator.
    """
    if not config.USE_MOCK_WEATHER:
        result = _fetch_open_meteo(lat, lon, timestamps)
        if result is not None:
            return result

    return _mock_weather(timestamps, lat, lon)
