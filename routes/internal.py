"""Hidden internal endpoints for trusted admin operations."""

from __future__ import annotations

import hmac
import logging
from flask import Blueprint, abort, jsonify, request

from config import config
from services.ledger_service import verify_chain

logger = logging.getLogger(__name__)
internal_bp = Blueprint("internal", __name__)


def _authorize_internal_request() -> None:
    token = request.headers.get("X-Internal-Auth", "")
    if config.LEDGER_ADMIN_TOKEN:
        if not hmac.compare_digest(token, config.LEDGER_ADMIN_TOKEN):
            abort(404)
        return

    if request.remote_addr not in {"127.0.0.1", "::1"}:
        abort(404)


@internal_bp.route("/internal/verify-ledger", methods=["GET"])
def verify_ledger() -> object:
    _authorize_internal_request()
    result = verify_chain()
    return jsonify(result)
