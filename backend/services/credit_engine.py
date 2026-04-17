class CreditEngine:
    def __init__(self):
        # In-memory wallet state (User ID -> Total Credits)
        self.wallets = {"farmer_001": 0.0, "farmer_002": 15.5}
        self.CREDIT_MULTIPLIER = 0.02 # 1 kg of methane reduction = 0.02 Carbon Credits

    def calculate_and_issue(self, user_id, baseline_methane, actual_methane):
        reduction = baseline_methane - actual_methane
        
        if reduction <= 0:
            return {
                "user_id": user_id,
                "credits_earned": 0.0,
                "total_balance": self.wallets.get(user_id, 0.0),
                "message": "No methane reduction detected. No credits issued."
            }

        credits_earned = round(reduction * self.CREDIT_MULTIPLIER, 4)
        
        # Update in-memory state
        if user_id not in self.wallets:
            self.wallets[user_id] = 0.0
        self.wallets[user_id] += credits_earned

        return {
            "user_id": user_id,
            "credits_earned": credits_earned,
            "total_balance": round(self.wallets[user_id], 4),
            "message": f"Successfully issued {credits_earned} credits for reducing {round(reduction, 2)} kg of CH4."
        }