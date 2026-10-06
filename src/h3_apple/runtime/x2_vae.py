"""Optional H3 X2 latent decoder, sharing the H3 core.

Checkpoint: speach1sdef178/MiniMax-H3-X2-Detail-VAE, af8c92d267c6849fec5032c35a65d5766737b338.
The weight license and author NOTICE apply. No Comfy/CUDA implementation is bundled.
"""
from dataclasses import replace
import gc
from pathlib import Path

import mlx.core as mx
import numpy as np

from .._vendor.fastvideo_mlx import minimax_h3_video_vae as core
from ..vsa_conversion import video_key_plan, transform_native
from .vae import make_compiled_block
from .quantization import linear_fp16


def pixel_shuffle(packed):
    """RGB-major (R00,R01,R10,R11,...) NCTHW -> doubled N3THW."""
    if packed.ndim != 5 or packed.shape[1] != 12:
        raise ValueError('X2 requires twelve packed RGB channels')
    b, _, t, h, w = packed.shape
    return mx.contiguous(packed.reshape(b, 3, 2, 2, t, h, w).transpose(0, 1, 4, 5, 2, 6, 3)).reshape(b, 3, t, h * 2, w * 2)


class X2VideoVAE(core.MLXMiniMaxH3VideoVAE):
    """Floating decoder: FP16 projections/SDPA with FP32 residuals and norms."""
    def __init__(self, weights, config, *, observer=None):
        super().__init__(weights, config, has_encoder=False)
        self.observer = observer
        self.traces = []
        self.compiled_block = make_compiled_block(core, self.traces, integer=None)
        self.block_calls = 0

    def _decoder_linear(self, x, weight, bias=None):
        return linear_fp16(x, weight, bias)

    def _decoder_block(self, *args, **kwargs):
        self.block_calls += 1
        return self.compiled_block(*args, **kwargs)

    def _decode_clip(self, z):
        before = self.block_calls
        output = super()._decode_clip(z)
        mx.eval(output)
        if self.block_calls - before != 36 or not bool(mx.all(mx.isfinite(output)).item()):
            raise ValueError('Incomplete or nonfinite X2 decoder tile')
        if self.observer is not None:
            self.observer.tile()
        return output

    def denormalize_pixels(self, sample):
        mean = mx.array(np.repeat(np.asarray(core.PIXEL_MEAN, np.float32), 4).reshape(1, 12, 1, 1, 1))
        std = mx.array(np.repeat(np.asarray(core.PIXEL_STD, np.float32), 4).reshape(1, 12, 1, 1, 1))
        return pixel_shuffle(sample.astype(mx.float32) * std + mean)

def load_x2(path, *, observer=None):
    path = Path(path)
    source = mx.load(str(path))
    if source['decoder.proj_out.weight'].shape != (12288, 2048):
        raise ValueError('Expected the pinned twelve-channel X2 output head')
    weights, mapped = {}, []
    for key, tensor in source.items():
        # Encoder and B32 source-image enhancement are separate operations.
        if key.startswith(('detail_b32.', 'encoder.', 'quant_conv.')):
            continue
        plan = video_key_plan(key)
        for target, transform in plan:
            value = transform_native(tensor, transform, heads=32, head_dim=64, xp=mx).astype(mx.float32)
            if value.ndim == 5: value = mx.contiguous(value.transpose(0, 2, 3, 4, 1))
            if target in weights: raise ValueError('Duplicate X2 parameter: '+target)
            mx.eval(value)
            weights[target] = value
            mapped.append((key, target, transform))
    config = replace(core.MiniMaxH3VideoVAEConfigView(), out_channels=12,
        latents_mean=tuple(np.asarray(source['latents_mean']).tolist()),
        latents_std=tuple(np.asarray(source['latents_std']).tolist()))
    del source
    gc.collect(); mx.clear_cache()
    model = X2VideoVAE(weights, config, observer=observer)
    model.mapping = mapped
    if len(model._decoder_blocks()) != 36 or any(len(block) != 16 for block in model._decoder_blocks()):
        raise ValueError('Incomplete X2 decoder block mapping')
    return model
