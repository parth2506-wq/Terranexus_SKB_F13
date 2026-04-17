"""CarbonKarma dMRV Carbon Intelligence Platform — Part 1 Backend."""
from __future__ import annotations
import logging, time
from flask import Flask, jsonify, Response, g, request

from config import config
#from routes import satellite_bp, fusion_bp, awd_bp, methane_bp
from routes import pipeline_bp

logging.basicConfig(
    level=logging.DEBUG if config.FLASK_DEBUG else logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("carbonkarma")

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # CORS without flask-cors dependency
    @app.after_request
    def _cors(response: Response) -> Response:
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return response

    @app.before_request
    def _start(): g.t0 = time.perf_counter()

    @app.after_request
    def _log(response: Response) -> Response:
        ms = (time.perf_counter() - getattr(g, "t0", time.perf_counter())) * 1000
        logger.info("%s %s → %d (%.0f ms)", request.method, request.path, response.status_code, ms)
        return response

    app.register_blueprint(pipeline_bp, url_prefix="/api")

    @app.route("/health", methods=["GET"])
    def health(): return jsonify({"status": "ok", "service": "CarbonKarma-Part1"})

    @app.route("/", methods=["GET"])
    def index():
        return jsonify({"service": "CarbonKarma dMRV Carbon Intelligence Platform", "part": 1,
                        "version": "1.0.0",
                        "endpoints": ["POST /satellite-data","POST /fusion-data","POST /awd-status","POST /methane","GET /health"]})

    @app.errorhandler(404)
    def not_found(e): return jsonify({"error": "Not found."}), 404
    @app.errorhandler(500)
    def err500(e): return jsonify({"error": "Internal server error."}), 500

    return app

if __name__ == "__main__":
    from pipeline import warmup_models
    logger.info("🌾 CarbonKarma Part-1 starting…")
    warmup_models()
    app = create_app()
    app.run(host="0.0.0.0", port=config.PORT, debug=config.FLASK_DEBUG, use_reloader=False)
