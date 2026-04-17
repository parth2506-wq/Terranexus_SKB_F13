"""CarbonKarma — AWD Detection Engine (Part 1, fixed cycle detection)."""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from config import config
from models.lstm_awd import LSTMAWDDetector, build_lstm, run_lstm, AWD_FEATURE_COLS
from utils.time_series import structure_time_series, normalise_features, df_to_tensor

logger = logging.getLogger(__name__)
_FLOODED = "flooded"; _DRY = "dry"; _TRANSITION = "transition"

def _water_state(wp):
    if wp >= config.AWD_FLOOD_THRESHOLD: return _FLOODED
    if wp <= config.AWD_DRY_THRESHOLD:   return _DRY
    return _TRANSITION

def _detect_cycles(fused_records):
    """
    Detect FLOODED → (TRANSITION) → DRY → (TRANSITION) → FLOODED cycles.
    Records both direct and transition-mediated state changes.
    """
    n_cycles = 0; irr = []; rain_ev = []; seq = []
    prev_definite = None   # last definite state (non-transition)
    in_dry_phase = False
    dry_streak = 0

    for rec in fused_records:
        ts = rec["timestamp"]; wp = rec["water_level"]; rain = rec["rainfall"]
        state = _water_state(wp)
        seq.append({"timestamp": ts, "state": state, "water_level": round(wp, 4)})

        definite = state if state != _TRANSITION else prev_definite

        # Transition from flooded → dry phase
        if prev_definite == _FLOODED and definite == _DRY:
            in_dry_phase = True
            dry_streak = 0

        if in_dry_phase and definite == _DRY:
            dry_streak += 1

        # Re-flooding after a dry phase → complete cycle
        if in_dry_phase and dry_streak >= 1 and definite == _FLOODED and prev_definite == _DRY:
            n_cycles += 1
            ev = {"timestamp": ts, "water_level": round(wp, 4), "rainfall_mm": round(rain, 2)}
            (rain_ev if rain >= 10.0 else irr).append(ev)
            in_dry_phase = False
            dry_streak = 0

        if state != _TRANSITION:
            prev_definite = state

    return n_cycles, irr, rain_ev, seq

def _prep_lstm_input(fused_records, device):
    rows = [{"timestamp": r["timestamp"], "water_prob_mean": r["water_prob_mean"],
             "ndvi_mean": r["ndvi_mean"], "lst_celsius_norm": r["lst_celsius_norm"],
             "rainfall_norm": r["rainfall_norm"], "vv_mean": r["vv_mean"],
             "vh_mean": r["vh_mean"]} for r in fused_records]
    df = structure_time_series(rows, AWD_FEATURE_COLS)
    df = normalise_features(df, AWD_FEATURE_COLS)
    return df_to_tensor(df, AWD_FEATURE_COLS, device=device)

def _confidence(lstm_signal, n_cycles, n_steps):
    lc = lstm_signal if lstm_signal > 0.5 else 1.0 - lstm_signal
    cc = min(n_cycles / 5.0, 1.0)
    vc = min(n_steps / 15.0, 1.0)
    return round(float(np.clip(0.45*lc + 0.40*cc + 0.15*vc, 0, 1)), 4)

def detect_awd(fused_records, lstm_model=None, device=None):
    device = device or config.MODEL_DEVICE
    if lstm_model is None: lstm_model = build_lstm(device=device)
    if not fused_records:
        return {"awd_status": "uncertain", "confidence": 0.0, "lstm_signal": 0.0,
                "cycles": 0, "irrigation_events": [], "rain_events": [],
                "flood_dry_sequence": [], "per_step_status": []}
    try:
        seq_t = _prep_lstm_input(fused_records, device)
        lstm_out = run_lstm(lstm_model, seq_t)
        lstm_signal = lstm_out["awd_signal"]
    except Exception as e:
        logger.warning("LSTM failed: %s", e); lstm_signal = 0.5

    n_cycles, irr, rain_ev, flood_dry_seq = _detect_cycles(fused_records)

    if lstm_signal > 0.65 and n_cycles >= 2:  awd_status = "active_awd"
    elif n_cycles >= 1 and lstm_signal > 0.4: awd_status = "active_awd"
    elif lstm_signal < 0.35 and n_cycles == 0: awd_status = "conventional"
    else: awd_status = "uncertain"

    per_step = [{"timestamp": r["timestamp"], "water_level": r["water_level"],
                 "state": _water_state(r["water_level"]),
                 "flood_type": r["flood_type"]} for r in fused_records]

    for r in fused_records: r["awd_status"] = awd_status

    return {"awd_status": awd_status,
            "confidence": _confidence(lstm_signal, n_cycles, len(fused_records)),
            "lstm_signal": round(lstm_signal, 4), "cycles": n_cycles,
            "irrigation_events": irr, "rain_events": rain_ev,
            "flood_dry_sequence": flood_dry_seq, "per_step_status": per_step}
