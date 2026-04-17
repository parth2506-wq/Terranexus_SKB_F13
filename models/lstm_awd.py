"""
CarbonKarma — LSTM AWD Detector.
PyTorch LSTM when available; stateful numpy GRU-like fallback otherwise.
"""
from __future__ import annotations
from typing import List, Optional, Dict
import numpy as np
from config import config
from utils.torch_compat import TORCH_AVAILABLE, sigmoid

AWD_FEATURE_COLS = ["water_prob_mean","ndvi_mean","lst_celsius_norm","rainfall_norm","vv_mean","vh_mean"]
N_INPUT_FEATURES = len(AWD_FEATURE_COLS)

if TORCH_AVAILABLE:
    import torch, torch.nn as nn
    class LSTMAWDDetector(nn.Module):
        def __init__(self, n_features=N_INPUT_FEATURES, hidden_size=config.LSTM_HIDDEN_SIZE, num_layers=config.LSTM_NUM_LAYERS, dropout=0.2):
            super().__init__()
            self.hidden_size = hidden_size; self.num_layers = num_layers
            self.lstm = nn.LSTM(n_features, hidden_size, num_layers, batch_first=True, dropout=dropout if num_layers>1 else 0.0)
            self.ln = nn.LayerNorm(hidden_size)
            self.head = nn.Sequential(nn.Linear(hidden_size,32), nn.ReLU(True), nn.Dropout(0.1), nn.Linear(32,1), nn.Sigmoid())
        def forward(self, x, h0=None, c0=None):
            B,device = x.size(0), x.device
            if h0 is None: h0 = torch.zeros(self.num_layers,B,self.hidden_size,device=device)
            if c0 is None: c0 = torch.zeros(self.num_layers,B,self.hidden_size,device=device)
            out,(hn,cn) = self.lstm(x,(h0,c0))
            hf = self.ln(out[:,-1,:])
            return self.head(hf), hf, (hn,cn)
else:
    class LSTMAWDDetector: pass  # type: ignore

def _numpy_lstm(sequence: np.ndarray) -> Dict:
    """Exponential-weighted smoothing + threshold logic as LSTM equivalent."""
    # sequence: (seq_len, n_features)
    water_col = 0   # water_prob_mean index
    ndvi_col  = 1
    rain_col  = 3
    water_series = sequence[:, water_col]
    ndvi_series  = sequence[:, ndvi_col]
    rain_series  = sequence[:, rain_col]

    # Smoothed water level
    alpha = 0.3
    smooth = np.zeros_like(water_series)
    smooth[0] = water_series[0]
    for i in range(1, len(water_series)):
        smooth[i] = alpha * water_series[i] + (1 - alpha) * smooth[i-1]

    # Detect alternations: variance of smoothed series indicates AWD
    variance = float(np.var(smooth))
    mean_water = float(np.mean(smooth))
    mean_ndvi  = float(np.mean(ndvi_series))
    mean_rain  = float(np.mean(rain_series))

    # AWD signal: high variance + moderate mean water + high NDVI
    awd_raw = (variance * 8.0) + (1.0 - abs(mean_water - 0.45) * 2.0) * 0.3 + mean_ndvi * 0.2
    awd_signal = float(np.clip(sigmoid(awd_raw - 1.5), 0, 1))

    # Hidden vector: key temporal statistics as pseudo-hidden-state
    n = config.LSTM_HIDDEN_SIZE
    base = np.concatenate([
        smooth,                                          # smoothed water
        ndvi_series,                                     # ndvi
        np.array([variance, mean_water, mean_ndvi]),    # summary stats
    ])
    if len(base) < n:
        base = np.tile(base, (n // len(base) + 1))[:n]
    hidden = base[:n].astype(np.float32)
    hidden = (hidden - hidden.min()) / max(hidden.max() - hidden.min(), 1e-9)

    return {"awd_signal": awd_signal, "hidden_vector": hidden.tolist()}

def build_lstm(device=None):
    if TORCH_AVAILABLE:
        m = LSTMAWDDetector().to(device or config.MODEL_DEVICE)
        m.eval(); return m
    return None

def run_lstm(model, sequence_tensor) -> Dict:
    if TORCH_AVAILABLE and model is not None:
        with torch.no_grad():
            sig, hf, _ = model(sequence_tensor)
            return {"awd_signal": float(sig.squeeze().cpu()), "hidden_vector": hf.squeeze(0).cpu().tolist()}
    # numpy path: sequence_tensor is np.ndarray (seq_len, n_features) or tensor
    try:
        seq = sequence_tensor.squeeze(0).numpy() if hasattr(sequence_tensor, 'numpy') else np.array(sequence_tensor)
    except Exception:
        seq = np.array(sequence_tensor)
    return _numpy_lstm(seq)
