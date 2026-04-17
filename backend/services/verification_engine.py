class VerificationEngine:
    def __init__(self):
        # Baseline expectations for AWD during a drying phase
        self.max_rain_allowance = 10.0 # mm

    def verify_awd_compliance(self, fusion_data):
        water_level = fusion_data.get("water_level", 0.0)
        rainfall = fusion_data.get("rainfall", 0.0)
        awd_status = fusion_data.get("awd_status", False)
        
        confidence = 0.0
        explanation = ""
        is_verified = False

        # Logic: If model detects AWD (drying) and there is no rain, high confidence.
        if awd_status is True:
            if rainfall < self.max_rain_allowance:
                confidence = 0.95
                is_verified = True
                explanation = "AWD compliance verified. Drying phase detected with negligible rainfall intervention."
            else:
                confidence = 0.40
                is_verified = False
                explanation = "AWD status contested. High rainfall detected during expected drying phase (Natural Event)."
        
        # Logic: If model detects flooded field, check if it was rain or irrigation
        else:
            if rainfall > self.max_rain_allowance:
                confidence = 0.85
                is_verified = False # Not AWD, but not farmer's fault
                explanation = "Field is flooded due to heavy rainfall (Act of Nature). AWD cannot be verified currently."
            else:
                confidence = 0.90
                is_verified = False
                explanation = "Field is artificially flooded (Irrigation). Farmer is NOT practicing AWD."

        return {
            "is_verified": is_verified,
            "confidence_score": confidence,
            "explanation": explanation,
            "timestamp": fusion_data.get("timestamp")
        }