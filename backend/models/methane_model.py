import torch
import torch.nn as nn

class MethanePredictor(nn.Module):
    def __init__(self):
        super(MethanePredictor, self).__init__()
        # Features: [water_probability, temperature, rainfall, awd_days]
        self.fc1 = nn.Linear(4, 16)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(16, 1)

    def forward(self, water_prob, temp, rainfall, awd_days=10):
        # Convert scalar inputs into a batch tensor
        x = torch.tensor([[water_prob, temp, rainfall, awd_days]], dtype=torch.float32)
        x = self.fc1(x)
        x = self.relu(x)
        methane_val = self.fc2(x)
        
        return {
            "value": float(methane_val.item()),
            "category": "High" if methane_val.item() > 50.0 else "Low"
        }