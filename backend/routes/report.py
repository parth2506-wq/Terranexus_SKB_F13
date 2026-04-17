from flask import Blueprint, request, jsonify
from services.llm_service import LLMReportingService
from config.settings import Config

report_bp = Blueprint('report', __name__)
llm_service = LLMReportingService()

@report_bp.route('/report', methods=['POST'])
def create_report():
    try:
        data = request.json
        fusion_data = data.get("fusion_data", {})
        verification_data = data.get("verification_data", {})
        
        if not Config.OPENROUTER_API_KEY:
            return jsonify({"error": "OPENROUTER_API_KEY is missing in .env"}), 500

        result = llm_service.generate_report(fusion_data, verification_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500