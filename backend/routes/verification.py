from flask import Blueprint, request, jsonify
from services.verification_engine import VerificationEngine

verification_bp = Blueprint('verification', __name__)
verifier = VerificationEngine()

@verification_bp.route('/verification', methods=['POST'])
def verify_data():
    try:
        fusion_data = request.json
        if not fusion_data:
            return jsonify({"error": "Fusion data payload required"}), 400
            
        result = verifier.verify_awd_compliance(fusion_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500