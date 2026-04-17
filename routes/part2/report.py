"""POST /report — Generate full MRV PDF report."""
from __future__ import annotations
import os
from flask import Blueprint, request, jsonify, send_file
from services.pipeline_part2 import run_part2_pipeline

report_bp = Blueprint("report", __name__)

@report_bp.route("/report", methods=["POST"])
def report():
    body     = request.get_json(silent=True) or {}
    lat      = body.get("lat"); lon = body.get("lon"); geojson = body.get("geojson")
    if lat is None and lon is None and geojson is None:
        return jsonify({"error": "Provide lat+lon or geojson"}), 400
    try:
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "lat/lon must be numeric"}), 400

    farm_id   = body.get("farm_id", "farm_001")
    n_steps   = max(1, min(int(body.get("n_steps", 12)), 50))
    step_days = max(1, int(body.get("step_days", 10)))

    try:
        result = run_part2_pipeline(
            lat=lat, lon=lon, geojson=geojson,
            farm_id=farm_id, n_steps=n_steps, step_days=step_days,
            generate_pdf=True,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    report_meta = result.get("report", {})
    return jsonify({
        "status": "success",
        "farm_id": farm_id,
        "report": report_meta,
        "verification": result["verification"],
        "credits_earned": result["credits"]["credits_earned"],
        "total_balance": result["credits"]["total_balance"],
        "farm_score": result["analytics"]["farm_score"],
        "download_hint": f"GET /report/download?path={report_meta.get('file_name', '')}",
    })


@report_bp.route("/report/download", methods=["GET"])
def report_download():
    """Serve a previously generated report file."""
    fname = request.args.get("path", "")
    if not fname or ".." in fname:
        return jsonify({"error": "Invalid path"}), 400
    fpath = os.path.join(os.getenv("REPORT_OUTPUT_DIR", "./reports"), fname)
    if not os.path.exists(fpath):
        return jsonify({"error": "Report not found"}), 404
    mime = "application/pdf" if fpath.endswith(".pdf") else "text/plain"
    return send_file(fpath, mimetype=mime, as_attachment=True, download_name=fname)


@report_bp.route("/report/list", methods=["GET"])
def report_list():
    farm_id = request.args.get("farm_id", "farm_001")
    from db.store import get_store
    return jsonify({"farm_id": farm_id, "reports": get_store().get_reports(farm_id)})
