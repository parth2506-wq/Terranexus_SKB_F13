from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

import torch


class FusionEngine:
    """Central orchestrator that fuses model and weather outputs."""

    def __init__(self) -> None:
        self._awd_threshold = 0.5

    def process_fusion(
        self,
        sar_tensor: torch.Tensor,
        opt_tensor: torch.Tensor,
        weather_data: Dict[str, Any],
        time_series_data: torch.Tensor,
    ) -> Dict[str, Any]:
        if sar_tensor.ndim != 4 or opt_tensor.ndim != 4:
            raise ValueError("sar_tensor and opt_tensor must be 4D tensors [B, C, H, W].")
        if time_series_data.ndim != 3:
            raise ValueError("time_series_data must be 3D tensor [B, T, F].")

        water_level = float(torch.sigmoid(sar_tensor.mean()).item())
        ndvi = float(weather_data.get("ndvi", torch.sigmoid(opt_tensor.mean()).item()))
        temperature = float(weather_data.get("temp", 30.0))
        rainfall = float(weather_data.get("rain", 0.0))
        awd_score = float(torch.sigmoid(time_series_data.mean()).item())
        awd_status = awd_score < self._awd_threshold
        methane_value = self._estimate_methane(water_level, ndvi, temperature, rainfall)
        soil_moisture = self._derive_soil_moisture(water_level, rainfall, temperature)
        flood_type = "rain" if rainfall >= 10.0 else "irrigation"

        timestamp = weather_data.get("timestamp") or datetime.now(timezone.utc).isoformat()
        location = weather_data.get("location", {"lat": 0.0, "lon": 0.0})

        return {
            "location": location,
            "water_level": round(water_level, 4),
            "ndvi": round(ndvi, 4),
            "temperature": round(temperature, 2),
            "rainfall": round(rainfall, 2),
            "soil_moisture": round(soil_moisture, 2),
            "flood_type": flood_type,
            "awd_status": awd_status,
            "methane_value": round(methane_value, 2),
            "timestamp": timestamp,
        }

    @staticmethod
    def _derive_soil_moisture(water_level: float, rainfall: float, temperature: float) -> float:
        value = (water_level * 70.0) + (rainfall * 0.8) - (temperature * 0.5)
        return max(0.0, min(100.0, value))

    @staticmethod
    def _estimate_methane(
        water_level: float,
        ndvi: float,
        temperature: float,
        rainfall: float,
    ) -> float:
        return max(0.0, 28.0 + (water_level * 45.0) - (ndvi * 12.0) + (temperature * 0.6) + (rainfall * 0.3))
