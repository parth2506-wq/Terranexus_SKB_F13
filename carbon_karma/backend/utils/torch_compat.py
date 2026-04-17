try:
    import torch

    TORCH_AVAILABLE = True

    def sigmoid(x):
        if isinstance(x, torch.Tensor):
            return torch.sigmoid(x)
        import math
        return 1 / (1 + math.exp(-x))

    def softplus(x):
        if isinstance(x, torch.Tensor):
            return torch.nn.functional.softplus(x)
        import math
        return math.log(1 + math.exp(x))

except ImportError:
    TORCH_AVAILABLE = False

    import numpy as np

    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    def softplus(x):
        return np.log1p(np.exp(x))