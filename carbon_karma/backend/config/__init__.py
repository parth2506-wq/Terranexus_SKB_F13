import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    MODEL_DEVICE = os.getenv("MODEL_DEVICE", "cpu")

    PATCH_SIZE = int(os.getenv("DEFAULT_SPATIAL_RESOLUTION", 10))
    TEMPORAL_DAYS = int(os.getenv("DEFAULT_TEMPORAL_DAYS", 90))

    CNN_OUT_FEATURES = int(os.getenv("CNN_OUT_FEATURES", 32))
    LSTM_HIDDEN_SIZE = int(os.getenv("LSTM_HIDDEN_SIZE", 64))
    LSTM_NUM_LAYERS = int(os.getenv("LSTM_NUM_LAYERS", 2))

    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    PORT = int(os.getenv("PORT", 5000))


config = Config()