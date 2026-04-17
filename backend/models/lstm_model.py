import torch
import torch.nn as nn

class AWDClassificationLSTM(nn.Module):
    def __init__(self, input_size=3, hidden_size=64, num_layers=2):
        super(AWDClassificationLSTM, self).__init__()
        # Input features: [water_level, ndvi, daily_rainfall]
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc1 = nn.Linear(hidden_size, 32)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, 2) # 2 classes: Compliant vs Non-Compliant

    def forward(self, time_series_tensor):
        # time_series_tensor shape: (batch_size, sequence_length, features)
        lstm_out, (hn, cn) = self.lstm(time_series_tensor)
        
        # Get the output from the last time step
        last_hidden_state = lstm_out[:, -1, :]
        
        x = self.fc1(last_hidden_state)
        x = self.relu(x)
        logits = self.fc2(x)
        return logits