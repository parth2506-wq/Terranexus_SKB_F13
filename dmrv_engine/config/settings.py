"""
Environment and API configuration.
Uses pydantic-settings for type-safe env variable loading.
Never logs or exposes credentials in error messages.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

try:
    from pydantic import Field, SecretStr
    from pydantic_settings import BaseSettings, SettingsConfigDict
    _PYDANTIC_AVAILABLE = True
except ImportError:
    _PYDANTIC_AVAILABLE = False

logger = logging.getLogger(__name__)


if _PYDANTIC_AVAILABLE:

    class DMRVSettings(BaseSettings):
        """Central settings. Loads from .env, shell env, then defaults."""

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",
        )

        # ── Sentinel Hub (OAuth2) ────────────────────────────────────────
        SENTINEL_HUB_CLIENT_ID:     SecretStr = Field(default=SecretStr(""))
        SENTINEL_HUB_CLIENT_SECRET: SecretStr = Field(default=SecretStr(""))
        SENTINEL_HUB_TOKEN_URL:     str = "https://services.sentinel-hub.com/oauth/token"
        SENTINEL_HUB_PROCESS_URL:   str = "https://services.sentinel-hub.com/api/v1/process"

        # ── Open-Meteo (no auth) ─────────────────────────────────────────
        OPEN_METEO_ARCHIVE_URL:  str = "https://archive-api.open-meteo.com/v1/archive"
        OPEN_METEO_FORECAST_URL: str = "https://api.open-meteo.com/v1/forecast"

        # ── SoilGrids (ISRIC, no auth) ───────────────────────────────────
        SOILGRIDS_BASE_URL: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
        SOILGRIDS_DEPTH:    str = "0-5cm"
        SOILGRIDS_VALUE:    str = "mean"

        # ── Sentinel-5P TROPOMI (Copernicus DataSpace) ──────────────────
        TROPOMI_CATALOG_URL: str = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
        COPERNICUS_USER:     SecretStr = Field(default=SecretStr(""))
        COPERNICUS_PASSWORD: SecretStr = Field(default=SecretStr(""))

        # ── HTTP behaviour ───────────────────────────────────────────────
        HTTP_TIMEOUT_S:  int = 30
        HTTP_RETRIES:    int = 3
        HTTP_BACKOFF_S:  float = 1.5

        # ── Model thresholds (scientific constants) ──────────────────────
        EVI_SATURATION_THRESHOLD:     float = 0.80
        NDWI_WATER_THRESHOLD:         float = 0.30
        VH_VV_WATER_THRESHOLD_DB:     float = -22.0
        METHANE_GWP_100_AR6:          float = 27.9
        CH4_BASELINE_FLOODED_KG_HA:   float = 480.0

        # ── Operational ──────────────────────────────────────────────────
        LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
        CACHE_DIR: Path = Path("./.cache")
        ENVIRONMENT: Literal["development", "staging", "production"] = "development"

        # ── Helpers ──────────────────────────────────────────────────────
        def sentinel_hub_configured(self) -> bool:
            return bool(
                self.SENTINEL_HUB_CLIENT_ID.get_secret_value()
                and self.SENTINEL_HUB_CLIENT_SECRET.get_secret_value()
            )

        def copernicus_configured(self) -> bool:
            return bool(
                self.COPERNICUS_USER.get_secret_value()
                and self.COPERNICUS_PASSWORD.get_secret_value()
            )

        def redacted_dict(self) -> dict:
            """Safe-to-log dict with secrets redacted."""
            d = self.model_dump()
            for k, v in d.items():
                if isinstance(v, SecretStr) or "SECRET" in k.upper() or "PASSWORD" in k.upper():
                    d[k] = "***REDACTED***"
            return d


    @lru_cache(maxsize=1)
    def get_settings() -> "DMRVSettings":
        """Cached singleton. Call this to access settings anywhere."""
        s = DMRVSettings()
        s.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Settings loaded (env=%s)", s.ENVIRONMENT)
        return s

else:
    # ── Minimal fallback when pydantic-settings isn't installed ──────────
    import os

    class DMRVSettings:
        def __init__(self):
            self.SENTINEL_HUB_CLIENT_ID     = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
            self.SENTINEL_HUB_CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")
            self.SENTINEL_HUB_TOKEN_URL     = "https://services.sentinel-hub.com/oauth/token"
            self.SENTINEL_HUB_PROCESS_URL   = "https://services.sentinel-hub.com/api/v1/process"
            self.OPEN_METEO_ARCHIVE_URL     = "https://archive-api.open-meteo.com/v1/archive"
            self.OPEN_METEO_FORECAST_URL    = "https://api.open-meteo.com/v1/forecast"
            self.SOILGRIDS_BASE_URL         = "https://rest.isric.org/soilgrids/v2.0/properties/query"
            self.SOILGRIDS_DEPTH            = "0-5cm"
            self.SOILGRIDS_VALUE            = "mean"
            self.TROPOMI_CATALOG_URL        = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
            self.COPERNICUS_USER            = os.getenv("COPERNICUS_USER", "")
            self.COPERNICUS_PASSWORD        = os.getenv("COPERNICUS_PASSWORD", "")
            self.HTTP_TIMEOUT_S             = int(os.getenv("HTTP_TIMEOUT_S", "30"))
            self.HTTP_RETRIES               = int(os.getenv("HTTP_RETRIES", "3"))
            self.HTTP_BACKOFF_S             = float(os.getenv("HTTP_BACKOFF_S", "1.5"))
            self.EVI_SATURATION_THRESHOLD   = 0.80
            self.NDWI_WATER_THRESHOLD       = 0.30
            self.VH_VV_WATER_THRESHOLD_DB   = -22.0
            self.METHANE_GWP_100_AR6        = 27.9
            self.CH4_BASELINE_FLOODED_KG_HA = 480.0
            self.LOG_LEVEL                  = os.getenv("LOG_LEVEL", "INFO")
            self.CACHE_DIR                  = Path(os.getenv("CACHE_DIR", "./.cache"))
            self.ENVIRONMENT                = os.getenv("ENVIRONMENT", "development")
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        def sentinel_hub_configured(self) -> bool:
            return bool(self.SENTINEL_HUB_CLIENT_ID and self.SENTINEL_HUB_CLIENT_SECRET)

        def copernicus_configured(self) -> bool:
            return bool(self.COPERNICUS_USER and self.COPERNICUS_PASSWORD)

        def redacted_dict(self) -> dict:
            return {k: ("***REDACTED***" if "SECRET" in k or "PASSWORD" in k else v)
                    for k, v in vars(self).items()}


    @lru_cache(maxsize=1)
    def get_settings() -> "DMRVSettings":
        return DMRVSettings()
