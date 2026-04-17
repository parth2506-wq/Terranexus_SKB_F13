from flask import Blueprint, request, jsonify
from services.credit_engine import CreditEngine

credits_bp = Blueprint('credits', __name__)
credit_engine = CreditEngine()

@credits_bp.route('/credits', methods=['POST'])
def issue_credits():
    try:
        data = request.json
        user_id = data.get("user_id", "farmer_001")
        baseline_methane = data.get("baseline_methane", 100.0)
        actual_methane = data.get("actual_methane", 0.0)
        
        result = credit_engine.calculate_and_issue(user_id, baseline_methane, actual_methane)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500