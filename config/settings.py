"""
CarbonKarma — Global configuration and environment loading.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "1") == "1"
    PORT: int = int(os.getenv("PORT", 5000))

    # Feature flags
    USE_MOCK_WEATHER: bool = os.getenv("USE_MOCK_WEATHER", "true").lower() == "true"

    # Sentinel Hub credentials (optional)
    SENTINEL_HUB_CLIENT_ID: str = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
    SENTINEL_HUB_CLIENT_SECRET: str = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")

    # Geospatial
    DEFAULT_SPATIAL_RESOLUTION: int = int(os.getenv("DEFAULT_SPATIAL_RESOLUTION", 10))
    DEFAULT_TEMPORAL_DAYS: int = int(os.getenv("DEFAULT_TEMPORAL_DAYS", 90))

    # Simulated image patch size (pixels)
    PATCH_SIZE: int = 64

    # PyTorch device
    MODEL_DEVICE: str = os.getenv("MODEL_DEVICE", "cpu")

    # LSTM
    LSTM_HIDDEN_SIZE: int = int(os.getenv("LSTM_HIDDEN_SIZE", 64))
    LSTM_NUM_LAYERS: int = int(os.getenv("LSTM_NUM_LAYERS", 2))

    # CNN
    CNN_OUT_FEATURES: int = int(os.getenv("CNN_OUT_FEATURES", 32))

    # Methane thresholds (mg CH4 / m2 / day)
    METHANE_LOW_THRESHOLD: float = 150.0
    METHANE_HIGH_THRESHOLD: float = 350.0

    # AWD detection
    AWD_FLOOD_THRESHOLD: float = 0.55      # water probability
    AWD_DRY_THRESHOLD: float = 0.25
    AWD_MIN_CYCLE_DAYS: int = 5


    # ── PART 2 ────────────────────────────────────────────────────────────

    # OpenRouter LLM (free tier works with any OpenRouter key)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

    # ChromaDB (optional — falls back to SQLite vector store)
    USE_CHROMADB: bool = os.getenv("USE_CHROMADB", "false").lower() == "true"
    CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", "./db/chromadb")

    # SQLite persistence path (always available)
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "./db/carbonkarma.db")

    # Carbon credit economics
    CREDIT_PRICE_USD: float = float(os.getenv("CREDIT_PRICE_USD", "15.0"))
    CREDIT_PER_TON_CO2: float = 1.0           # 1 credit = 1 tonne CO2e
    METHANE_GWP_100: float = 27.9             # AR6 GWP-100 (CH4 → CO2e)
    BASELINE_EMISSION_KG_HA: float = 480.0    # CF season baseline kg CH4/ha

    # Report
    REPORT_OUTPUT_DIR: str = os.getenv("REPORT_OUTPUT_DIR", "./reports")

    # Verification thresholds
    VERIFICATION_NDVI_MIN: float = 0.25       # min NDVI for active crop
    VERIFICATION_TEMP_MAX_C: float = 45.0
    VERIFICATION_CLOUD_MAX: float = 0.40      # max cloud fraction per step


config = Config()
