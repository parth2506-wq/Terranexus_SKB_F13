"""
CarbonKarma — Methane Estimator.
PyTorch MLP when available; physics-informed numpy fallback otherwise.
"""
from __future__ import annotations
from typing import List, Dict, Optional
import numpy as np
from config import config
from utils.torch_compat import TORCH_AVAILABLE, sigmoid, softplus

SCALAR_FEATURES = ["ndvi_mean","lst_celsius_norm","rainfall_norm","soil_moisture_mean"]
N_SCALAR = len(SCALAR_FEATURES)
CF_BASELINE = 400.0

if TORCH_AVAILABLE:
    import torch, torch.nn as nn
    class MethaneEstimator(nn.Module):
        def __init__(self, cnn_features=config.CNN_OUT_FEATURES, lstm_hidden=config.LSTM_HIDDEN_SIZE, n_scalar=N_SCALAR, hidden_dim=128):
            super().__init__()
            in_dim = cnn_features + lstm_hidden + n_scalar
            self.encoder = nn.Sequential(nn.Linear(in_dim,hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU(), nn.Dropout(0.15), nn.Linear(hidden_dim,64), nn.GELU(), nn.Dropout(0.1))
            self.flux_head = nn.Sequential(nn.Linear(64,1), nn.Softplus())
            self.red_head  = nn.Sequential(nn.Linear(64,1), nn.Sigmoid())
        def forward(self, cnn, lstm, scalar):
            enc = self.encoder(torch.cat([cnn, lstm, scalar], -1))
            return self.flux_head(enc) * 500 + 50, self.red_head(enc) * 80
else:
    class MethaneEstimator: pass  # type: ignore

def _numpy_methane(cnn_vec, lstm_vec, ndvi, lst_norm, rain_norm, soil_moist) -> Dict:
    """Physics-informed methane estimation."""
    # Aggregate CNN features (water signal strength)
    cnn_arr = np.array(cnn_vec, dtype=np.float32)
    water_signal = float(cnn_arr.mean()) * 2.0   # CNN captures water extent

    lstm_arr = np.array(lstm_vec, dtype=np.float32)
    awd_signal = float(lstm_arr[:10].mean())      # first 10 dims reflect AWD pattern

    # Methanogenesis drivers
    water_w  = np.clip(water_signal, 0, 1)
    temp_w   = np.clip(lst_norm, 0, 1)
    ndvi_w   = np.clip(ndvi, 0, 1)
    rain_w   = np.clip(rain_norm * 0.4, 0, 0.3)
    soil_w   = np.clip(soil_moist, 0, 1)

    # Q10 temperature scaling (methanogenesis doubles every 10 °C above 15 °C)
    temp_celsius_approx = lst_norm * 45 + 15
    q10_factor = 2.0 ** ((temp_celsius_approx - 25.0) / 10.0)
    q10_factor = float(np.clip(q10_factor, 0.5, 3.0))

    raw_score = (water_w * 0.40 + ndvi_w * 0.25 + temp_w * 0.15 + rain_w * 0.10 + soil_w * 0.10)
    flux = float(np.clip(raw_score * CF_BASELINE * q10_factor + 50, 50, 600))

    # AWD reduces methane proportional to dryness depth
    dry_intensity = 1.0 - water_w
    reduction = float(np.clip(dry_intensity * 70.0 * (1.0 + awd_signal * 0.2), 0, 80))
    if water_w > 0.7:   # continuously flooded
        reduction = float(np.random.uniform(0, 8))

    cat = "low" if flux < config.METHANE_LOW_THRESHOLD else ("high" if flux > config.METHANE_HIGH_THRESHOLD else "medium")
    return {"methane": round(flux, 2), "category": cat, "reduction_percent": round(reduction, 2)}

def build_methane_model(device=None):
    if TORCH_AVAILABLE:
        m = MethaneEstimator().to(device or config.MODEL_DEVICE)
        m.eval(); return m
    return None

def run_methane_model(model, cnn_feature_vector, lstm_hidden_vector, ndvi_mean, lst_celsius_norm, rainfall_norm, soil_moisture_mean, device=None) -> Dict:
    if TORCH_AVAILABLE and model is not None:
        with torch.no_grad():
            d = device or config.MODEL_DEVICE
            cnn_t = torch.tensor([cnn_feature_vector], dtype=torch.float32, device=d)
            lstm_t = torch.tensor([lstm_hidden_vector], dtype=torch.float32, device=d)
            sc_t   = torch.tensor([[ndvi_mean, lst_celsius_norm, rainfall_norm, soil_moisture_mean]], dtype=torch.float32, device=d)
            flux, red = model(cnn_t, lstm_t, sc_t)
            val = float(flux.squeeze().cpu())
            cat = "low" if val < config.METHANE_LOW_THRESHOLD else ("high" if val > config.METHANE_HIGH_THRESHOLD else "medium")
            return {"methane": round(val,2), "category": cat, "reduction_percent": round(float(red.squeeze().cpu()),2)}
    return _numpy_methane(cnn_feature_vector, lstm_hidden_vector, ndvi_mean, lst_celsius_norm, rainfall_norm, soil_moisture_mean)
