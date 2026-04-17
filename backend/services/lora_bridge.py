from __future__ import annotations

import json
import logging
import socket
import threading
from typing import Any, Dict

from config.settings import Config

logger = logging.getLogger(__name__)


class MeshMessengerBridge:
    def __init__(self, esp32_ip: str | None = None, esp32_port: int | None = None) -> None:
        self.esp32_ip = esp32_ip or Config.ESP32_IP
        self.esp32_port = esp32_port or Config.ESP32_PORT
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(2.0)

    def broadcast_alert(self, location: Dict[str, Any], alert_type: str, severity: str) -> None:
        payload = {
            "type": "EMERGENCY_ALERT",
            "ttl": 5,
            "alert_type": alert_type,
            "severity": severity,
            "location": location,
            "message": f"{severity}: {alert_type} at {location}",
        }
        threading.Thread(target=self._send_packet, args=(payload,), daemon=True).start()

    def _send_packet(self, payload: Dict[str, Any]) -> None:
        try:
            self.sock.sendto(json.dumps(payload).encode("utf-8"), (self.esp32_ip, self.esp32_port))
            logger.info("Mesh alert sent to %s:%s", self.esp32_ip, self.esp32_port)
        except Exception as exc:
            logger.warning("Mesh alert send failed: %s", exc)
