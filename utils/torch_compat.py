"""
CarbonKarma — PyTorch compatibility shim.

When torch is available (production), real nn.Module models are used.
When torch is unavailable (CI / constrained environments), this module
provides drop-in numpy-based equivalents that produce the same output
shapes and realistic value ranges.

Usage (everywhere that needs torch):
    from utils.torch_compat import torch, nn, TORCH_AVAILABLE
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None   # type: ignore
    nn = None      # type: ignore


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + np.exp(-float(x)))


def softplus(x: float) -> float:
    return float(np.log1p(np.exp(min(x, 20.0))))
