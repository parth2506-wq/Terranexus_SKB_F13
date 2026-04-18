"""
Immutable shadow ledger service for CarbonKarma.

This module writes pipeline summaries to a local append-only ledger file and
provides verification of hash chaining, signatures, and record integrity.

The ledger is intentionally silent in normal operation: only DEBUG-level logs
are emitted and the frontend is not aware of its existence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from config import config

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_SECRET_KEY_BYTES: Optional[bytes] = None


def _load_secret_key() -> bytes:
    secret = config.LEDGER_SECRET_KEY
    if secret:
        return secret.encode("utf-8")

    key_path = config.LEDGER_KEY_PATH
    if os.path.exists(key_path):
        try:
            with open(key_path, "r", encoding="utf-8") as handle:
                return handle.read().strip().encode("utf-8")
        except Exception as exc:
            logger.debug("Unable to read ledger key file: %s", exc)

    secret_bytes = os.urandom(32)
    try:
        os.makedirs(os.path.dirname(key_path) or ".", exist_ok=True)
        with open(key_path, "w", encoding="utf-8") as handle:
            handle.write(secret_bytes.hex())
    except Exception as exc:
        logger.debug("Unable to persist ledger key file: %s", exc)
    return secret_bytes


def _secret_key() -> bytes:
    global _SECRET_KEY_BYTES
    if _SECRET_KEY_BYTES is None:
        _SECRET_KEY_BYTES = _load_secret_key()
    return _SECRET_KEY_BYTES


def _canonical_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return round(float(value), 5)
    if isinstance(value, dict):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if hasattr(value, "tolist"):
        try:
            return _canonical_value(value.tolist())
        except Exception:
            pass
    return str(value)


def compute_hash(payload: Dict[str, Any]) -> str:
    canonical_payload = _canonical_value(payload)
    json_text = json.dumps(
        canonical_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(json_text.encode("utf-8")).hexdigest()


def _sign_hash(hash_value: str) -> str:
    return hmac.new(_secret_key(), hash_value.encode("utf-8"), hashlib.sha256).hexdigest()


def _proof_hash(hash_value: str, timestamp: str) -> str:
    return hashlib.sha256(f"{hash_value}:{timestamp}".encode("utf-8")).hexdigest()


def _read_ledger_entries(path: Optional[str] = None) -> List[Dict[str, Any]]:
    path = path or config.LEDGER_PATH
    entries: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return entries

    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                entries.append(json.loads(text))
    except Exception as exc:
        logger.debug("Failed reading ledger file: %s", exc)
    return entries


def read_ledger_entries(path: Optional[str] = None) -> List[Dict[str, Any]]:
    return _read_ledger_entries(path)


def _last_hash() -> str:
    entries = _read_ledger_entries()
    if not entries:
        return "0" * 64
    return entries[-1].get("hash", "0" * 64)


def _build_ledger_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    location = result.get("location", {})
    satellite_data = result.get("satellite_data", {})
    fusion_data = result.get("fusion_data", [])
    methane_data = result.get("methane", {})
    awd_result = result.get("awd_result")

    latest_fusion = fusion_data[-1] if fusion_data else {}

    def _summarise(records: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
        return [
            {k: _canonical_value(record.get(k)) for k in ["timestamp"] + keys if record.get(k) is not None}
            for record in records
        ]

    return {
        "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "location": {
            "lat": _canonical_value(location.get("lat")),
            "lon": _canonical_value(location.get("lon")),
            "bbox": _canonical_value(location.get("bbox")),
        },
        "satellite_inputs_summary": {
            "sentinel1": _summarise(
                satellite_data.get("sentinel1", []),
                ["vv_mean", "vh_mean", "water_prob_mean", "phenology_stage", "is_flooded"],
            ),
            "sentinel2": _summarise(
                satellite_data.get("sentinel2", []),
                ["ndvi_mean", "ndvi_std", "cloud_fraction", "phenology_stage"],
            ),
            "lst": _summarise(
                satellite_data.get("lst", []),
                ["lst_mean_celsius", "lst_std"],
            ),
            "weather": _canonical_value(satellite_data.get("weather", [])),
        },
        "fusion_output": [
            _canonical_value({
                "timestamp": record.get("timestamp"),
                "water_level": record.get("water_level"),
                "ndvi": record.get("ndvi"),
                "temperature": record.get("temperature"),
                "rainfall": record.get("rainfall"),
                "soil_moisture": record.get("soil_moisture"),
                "flood_type": record.get("flood_type"),
                "cnn_water_score": record.get("cnn_water_score"),
                "phenology_stage": record.get("phenology_stage"),
                "cloud_fraction": record.get("cloud_fraction"),
                "awd_status": record.get("awd_status"),
            })
            for record in fusion_data
        ],
        "methane_output": {
            "aggregate": _canonical_value(methane_data.get("aggregate")),
            "latest": _canonical_value(methane_data.get("latest")),
            "per_step": [
                _canonical_value(
                    {
                        "timestamp": step.get("timestamp"),
                        "ch4_flux": step.get("ch4_flux"),
                        "co2e": step.get("co2e"),
                        "water_level": step.get("water_level"),
                    }
                )
                for step in methane_data.get("per_step", [])
            ],
        },
        "awd_detection": _canonical_value(awd_result),
        "feature_vector": _canonical_value(latest_fusion.get("cnn_feature_vector")),
        "water_score": _canonical_value(latest_fusion.get("cnn_water_score")),
        "llm_insights_summary": _canonical_value(result.get("llm_insights_summary")),
    }


def write_to_ledger(result: Dict[str, Any]) -> None:
    if config.LEDGER_DISABLED:
        return

    payload = _build_ledger_payload(result)
    record_hash = compute_hash(payload)
    prev_hash = _last_hash()
    timestamp = payload["timestamp"]
    signature = _sign_hash(record_hash)
    proof_hash = _proof_hash(record_hash, timestamp)

    entry = {
        "hash": record_hash,
        "prev_hash": prev_hash,
        "timestamp": timestamp,
        "signature": signature,
        "proof_hash": proof_hash,
        "data": payload,
    }

    ledger_path = config.LEDGER_PATH
    try:
        os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
        with _LOCK:
            with open(ledger_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug("Ledger write completed: %s", record_hash)
    except Exception as exc:
        logger.debug("Ledger write failed: %s", exc, exc_info=True)


def schedule_ledger_write(result: Dict[str, Any]) -> None:
    if config.LEDGER_DISABLED:
        return

    thread = threading.Thread(target=write_to_ledger, args=(result,), daemon=True)
    thread.start()


def verify_chain() -> Dict[str, Any]:
    entries = _read_ledger_entries()
    if not entries:
        return {"valid": True, "broken_index": None, "entry_count": 0}

    previous_hash = "0" * 64
    for index, entry in enumerate(entries):
        data = entry.get("data", {})
        stored_hash = entry.get("hash")
        stored_prev = entry.get("prev_hash")
        stored_signature = entry.get("signature")

        computed_hash = compute_hash(data)
        if computed_hash != stored_hash or stored_prev != previous_hash:
            return {"valid": False, "broken_index": index, "entry_count": len(entries)}

        expected_signature = _sign_hash(stored_hash)
        if not hmac.compare_digest(expected_signature, str(stored_signature or "")):
            return {"valid": False, "broken_index": index, "entry_count": len(entries)}

        previous_hash = stored_hash

    return {"valid": True, "broken_index": None, "entry_count": len(entries)}
