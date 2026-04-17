"""
CarbonKarma dMRV Carbon Intelligence Platform — Part 1 + 2 Backend
Flask application factory.
"""
from __future__ import annotations
import logging, os, time
from flask import Flask, jsonify, Response, g, request

from config import config
from routes import (
    satellite_bp, fusion_bp, awd_bp, methane_bp,          # Part 1
    verification_bp, credits_bp, analytics_bp,              # Part 2
    report_bp, llm_bp,
)

logging.basicConfig(
    level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("carbonkarma")

# Ensure reports dir exists
os.makedirs(config.REPORT_OUTPUT_DIR, exist_ok=True)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # CORS (no flask-cors dependency)
    @app.after_request
    def _cors(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"]  = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,DELETE"
        return response

    @app.before_request
    def _start(): g.t0 = time.perf_counter()

    @app.after_request
    def _log(response: Response) -> Response:
        ms = (time.perf_counter() - getattr(g, "t0", time.perf_counter())) * 1000
        logger.info("%s %s → %d  (%.0f ms)", request.method, request.path,
                    response.status_code, ms)
        return response

    # ── Part 1 blueprints ─────────────────────────────────────────────────
    app.register_blueprint(satellite_bp)
    app.register_blueprint(fusion_bp)
    app.register_blueprint(awd_bp)
    app.register_blueprint(methane_bp)

    # ── Part 2 blueprints ─────────────────────────────────────────────────
    app.register_blueprint(verification_bp)
    app.register_blueprint(credits_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(llm_bp)

    # ── Health + index ────────────────────────────────────────────────────
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "CarbonKarma", "parts": [1, 2]})

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({
            "service": "CarbonKarma dMRV Carbon Intelligence Platform",
            "version": "2.0.0",
            "endpoints": {
                "part1": [
                    "POST /satellite-data",
                    "POST /fusion-data",
                    "POST /awd-status",
                    "POST /methane",
                ],
                "part2": [
                    "POST /verification",
                    "POST /credits",
                    "GET  /credits/wallet?farm_id=",
                    "POST /credits/retire",
                    "POST /analytics",
                    "POST /report",
                    "GET  /report/download?path=",
                    "GET  /report/list?farm_id=",
                    "POST /llm-insights",
                    "POST /llm-insights/explain",
                    "POST /llm-insights/alerts",
                    "POST /llm-insights/certificate",
                ],
                "system": ["GET /health"],
            }
        })

    @app.errorhandler(404)
    def not_found(e): return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e): return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def err500(e):
        logger.exception("Unhandled 500")
        return jsonify({"error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    from services.pipeline import warmup_models
    logger.info("🌾 CarbonKarma Part 1+2 backend starting…")
    warmup_models()
    app = create_app()
    app.run(host="0.0.0.0", port=config.PORT, debug=config.FLASK_DEBUG, use_reloader=False)
