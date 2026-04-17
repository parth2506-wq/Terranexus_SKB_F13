from flask import Blueprint, request, jsonify
from pipeline import run_full_pipeline

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/run", methods=["POST"])
def run_pipeline():
    try:
        data = request.get_json()

        lat = data.get("lat")
        lon = data.get("lon")
        geojson = data.get("geojson")

        n_steps = data.get("n_steps", 10)
        step_days = data.get("step_days", 10)

        result = run_full_pipeline(
            lat=lat,
            lon=lon,
            geojson=geojson,
            n_steps=n_steps,
            step_days=step_days
        )

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500