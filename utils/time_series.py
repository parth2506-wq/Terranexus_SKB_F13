"""CarbonKarma — Time-series utilities (no torch hard dependency)."""
from __future__ import annotations
from datetime import date, timedelta
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

from config import config

def generate_date_range(start=None, n_steps=10, step_days=10) -> List[str]:
    if start is None:
        base = date.today() - timedelta(days=n_steps * step_days)
    else:
        base = date.fromisoformat(start)
    return [(base + timedelta(days=i * step_days)).isoformat() for i in range(n_steps)]

def structure_time_series(timestep_records, feature_cols) -> pd.DataFrame:
    df = pd.DataFrame(timestep_records)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    for col in feature_cols:
        if col not in df.columns:
            df[col] = np.nan
    df[feature_cols] = df[feature_cols].ffill().bfill()
    return df

def normalise_features(df, feature_cols) -> pd.DataFrame:
    df = df.copy()
    for col in feature_cols:
        lo, hi = df[col].min(), df[col].max()
        rng = hi - lo
        df[col] = (df[col] - lo) / rng if rng > 1e-9 else 0.0
    return df

def df_to_tensor(df, feature_cols, device=None):
    arr = df[feature_cols].values.astype(np.float32)
    from utils.torch_compat import TORCH_AVAILABLE
    if TORCH_AVAILABLE:
        import torch
        return torch.from_numpy(arr).unsqueeze(0).to(device or config.MODEL_DEVICE)
    return arr  # return raw numpy for fallback path
