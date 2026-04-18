"""
SoilGrids v2.0 API service.

ISRIC SoilGrids provides global soil property predictions at 250m resolution.
API docs: https://www.isric.org/explore/soilgrids/soilgrids-access

Units returned by the API:
  soc  (Soil Organic Carbon): dg/kg → convert to g/kg by dividing by 10
  clay (Clay content %):      g/kg  → convert to % by dividing by 10
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from config.settings import get_settings
from utils.http import retry_get, HttpError

logger = logging.getLogger(__name__)


# ── Data transfer object ────────────────────────────────────────────────

@dataclass(frozen=True)
class SoilProperties:
    """Soil properties at a point. `None` for any property that couldn't be fetched."""
    latitude:   float
    longitude:  float
    depth:      str                              # e.g. "0-5cm"
    soc_g_per_kg:       Optional[float] = None   # Soil Organic Carbon, g/kg
    clay_percent:       Optional[float] = None   # Clay content, %
    sand_percent:       Optional[float] = None   # Optional
    bulk_density_kg_m3: Optional[float] = None   # Optional
    source:             str = "soilgrids"
    cached:             bool = False
    warnings:           list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.soc_g_per_kg is not None and self.clay_percent is not None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_complete"] = self.is_complete
        return d


# ── Service ─────────────────────────────────────────────────────────────

class SoilGridsService:
    """
    Fetches soil properties from SoilGrids v2.0 REST API.

    Usage:
        svc = SoilGridsService()
        soil = svc.fetch(lat=13.0827, lon=80.2707)
        if soil.is_complete:
            print(soil.soc_g_per_kg, soil.clay_percent)
    """

    # Properties requested (see https://www.isric.org/explore/soilgrids/faq-soilgrids)
    DEFAULT_PROPERTIES = ("soc", "clay", "sand", "bdod")

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.SOILGRIDS_BASE_URL
        self.depth    = self.settings.SOILGRIDS_DEPTH
        self.value    = self.settings.SOILGRIDS_VALUE

    # ── Public ──────────────────────────────────────────────────────────

    def fetch(
        self,
        lat: float,
        lon: float,
        properties: tuple[str, ...] = DEFAULT_PROPERTIES,
    ) -> SoilProperties:
        """
        Fetch soil properties at the given coordinate.

        Returns a `SoilProperties` dataclass. Any failed fetch yields
        `None` for the affected field and appends a warning; the call never
        raises — upstream callers must check `.is_complete`.
        """
        self._validate_coords(lat, lon)

        warnings: list[str] = []
        raw: dict = {}

        try:
            raw = retry_get(
                self.base_url,
                params={
                    "lat":      lat,
                    "lon":      lon,
                    "property": list(properties),
                    "depth":    self.depth,
                    "value":    self.value,
                },
                timeout=self.settings.HTTP_TIMEOUT_S,
                retries=self.settings.HTTP_RETRIES,
                backoff=self.settings.HTTP_BACKOFF_S,
            )
        except HttpError as e:
            logger.error("SoilGrids fetch failed for (%.4f, %.4f): %s", lat, lon, e)
            warnings.append(f"api_error: {e.status_code or 'network'}")
            return SoilProperties(
                latitude=lat, longitude=lon, depth=self.depth, warnings=warnings,
            )

        soc   = self._extract(raw, "soc",  warnings)
        clay  = self._extract(raw, "clay", warnings)
        sand  = self._extract(raw, "sand", warnings)
        bdod  = self._extract(raw, "bdod", warnings)

        # Unit conversions per SoilGrids docs
        soc_g_kg      = (soc / 10.0) if soc  is not None else None  # dg/kg → g/kg
        clay_pct      = (clay / 10.0) if clay is not None else None  # g/kg → %
        sand_pct      = (sand / 10.0) if sand is not None else None
        bulk_kg_m3    = (bdod * 10.0) if bdod is not None else None  # cg/cm³ → kg/m³

        return SoilProperties(
            latitude=lat, longitude=lon, depth=self.depth,
            soc_g_per_kg=soc_g_kg, clay_percent=clay_pct,
            sand_percent=sand_pct, bulk_density_kg_m3=bulk_kg_m3,
            warnings=warnings,
        )

    # ── Internal ────────────────────────────────────────────────────────

    @staticmethod
    def _validate_coords(lat: float, lon: float) -> None:
        if not (-90.0 <= lat <= 90.0):
            raise ValueError(f"Latitude out of range: {lat}")
        if not (-180.0 <= lon <= 180.0):
            raise ValueError(f"Longitude out of range: {lon}")

    @staticmethod
    def _extract(payload: dict, prop: str, warnings: list[str]) -> Optional[float]:
        """
        SoilGrids response shape (v2.0):
        {
          "properties": {
            "layers": [
              {
                "name": "soc",
                "depths": [
                  { "label": "0-5cm", "values": { "mean": 145 } },
                  ...
                ]
              }, ...
            ]
          }
        }
        """
        try:
            layers = payload.get("properties", {}).get("layers", [])
            for layer in layers:
                if layer.get("name") != prop:
                    continue
                for depth in layer.get("depths", []):
                    if depth.get("label") == get_settings().SOILGRIDS_DEPTH:
                        val = depth.get("values", {}).get("mean")
                        if val is None:
                            warnings.append(f"{prop}: null at depth")
                            return None
                        return float(val)
            warnings.append(f"{prop}: not in response")
            return None

        except (KeyError, TypeError, ValueError) as e:
            warnings.append(f"{prop}: parse error — {e}")
            return None
