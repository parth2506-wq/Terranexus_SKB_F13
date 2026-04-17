import torch
import torch.nn as nn

class WaterDetectionCNN(nn.Module):
    def __init__(self):
        super(WaterDetectionCNN, self).__init__()
        # Input: Multi-modal stacked tensor (SAR VV/VH + Optical NDWI) -> approx 4 channels
        self.conv1 = nn.Conv2d(in_channels=4, out_channels=16, kernel_size=3, padding=1)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.conv2 = nn.Conv2d(in_channels=16, out_channels=32, kernel_size=3, padding=1)
        
        # Adaptive pooling ensures consistent output size regardless of input image size
        self.adaptive_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, sar_tensor, opt_tensor):
        # Concatenate multi-modal inputs along channel dimension
        x = torch.cat((sar_tensor, opt_tensor), dim=1)
        x = self.conv1(x)
        x = self.relu(x)
        x = self.pool(x)
        x = self.conv2(x)
        x = self.relu(x)
        x = self.adaptive_pool(x)
        x = torch.flatten(x, 1)
        x = self.fc(x)
        return self.sigmoid(x).squeeze() # Returns a probability (0.0 to 1.0)