# Copyright 2026 H3 Apple contributors. Apache-2.0.
"""Native RMSNorm with the checkpoint's cast-before-learned-scale boundary."""
import torch
from torch import nn
from torch.nn import functional as F


class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps
        self._units = {}

    def forward(self, x):
        key = (x.device, x.dtype)
        if key not in self._units:
            self._units[key] = torch.ones_like(self.weight, device=x.device, dtype=x.dtype)
        return F.rms_norm(x, (x.shape[-1],), self._units[key], self.eps) * self.weight
