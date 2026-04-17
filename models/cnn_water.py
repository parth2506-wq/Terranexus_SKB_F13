"""
CarbonKarma — CNN Water Feature Extractor.
PyTorch path when available; physics-informed NumPy fallback otherwise.
"""
from __future__ import annotations
from typing import Dict
import numpy as np
from config import config
from utils.torch_compat import TORCH_AVAILABLE, sigmoid

if TORCH_AVAILABLE:
    import torch, torch.nn as nn

    class _ConvBlock(nn.Module):
        def __init__(self, in_ch, out_ch, pool=True):
            super().__init__()
            layers = [nn.Conv2d(in_ch, out_ch, 3, padding=1, bias=False), nn.BatchNorm2d(out_ch), nn.ReLU(True)]
            if pool: layers.append(nn.MaxPool2d(2, 2))
            self.block = nn.Sequential(*layers)
        def forward(self, x): return self.block(x)

    class CNNWaterExtractor(nn.Module):
        def __init__(self, out_features=config.CNN_OUT_FEATURES):
            super().__init__()
            self.features = nn.Sequential(_ConvBlock(2,16), _ConvBlock(16,32), _ConvBlock(32,64))
            self.gap = nn.AdaptiveAvgPool2d(1)
            self.projection = nn.Sequential(nn.Linear(64, out_features), nn.ReLU(True))
            self.water_head = nn.Sequential(nn.Linear(out_features, 1), nn.Sigmoid())
        def forward(self, x):
            p = self.gap(self.features(x)).flatten(1)
            fv = self.projection(p)
            return fv, self.water_head(fv)
else:
    class CNNWaterExtractor: pass   # type: ignore

def _numpy_cnn(vv, vh, out_features):
    import cv2
    feats = []
    for sz in [8, 4, 2]:
        for arr in [vv, vh]:
            p = cv2.resize(arr.astype(np.float32), (sz, sz), interpolation=cv2.INTER_AREA).ravel()
            feats.extend([p.mean(), p.std()])
    ratio = vh / np.maximum(vv, 1e-9)
    feats += [ratio.mean(), ratio.std()]
    gx = cv2.Sobel(vv.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(vv.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
    gm = np.sqrt(gx**2 + gy**2)
    feats += [gm.mean(), gm.std()]
    for p in [10, 25, 50, 75, 90]:
        feats += [float(np.percentile(vv, p)), float(np.percentile(vh, p))]
    arr = np.array(feats, dtype=np.float32)
    if len(arr) < out_features:
        arr = np.pad(arr, (0, out_features - len(arr)))
    else:
        arr = arr[:out_features]
    lo, hi = arr.min(), arr.max()
    if hi - lo > 1e-9: arr = (arr - lo) / (hi - lo)
    ws = sigmoid(-(vv.mean()*4 + vh.mean()*3 + gm.mean()*2) + 3.5)
    return {"feature_vector": arr.tolist(), "water_score": float(np.clip(ws, 0, 1))}

def build_cnn(device=None):
    if TORCH_AVAILABLE:
        m = CNNWaterExtractor(config.CNN_OUT_FEATURES).to(device or config.MODEL_DEVICE)
        m.eval(); return m
    return None

def run_cnn(model, vv_patch, vh_patch, device=None):
    if TORCH_AVAILABLE and model is not None:
        with torch.no_grad():
            d = device or config.MODEL_DEVICE
            vv_t = torch.from_numpy(vv_patch.astype(np.float32)).to(d)
            vh_t = torch.from_numpy(vh_patch.astype(np.float32)).to(d)
            # Combine into 4D tensor: (batch=1, channel=2, h, w)
            x = torch.stack([vv_t, vh_t], dim=0).unsqueeze(0)
            fv, ws = model(x)
            return {"feature_vector": fv.squeeze(0).cpu().tolist(), "water_score": float(ws.squeeze().cpu())}
    return _numpy_cnn(vv_patch, vh_patch, config.CNN_OUT_FEATURES)
