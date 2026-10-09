# SPDX-License-Identifier: Apache-2.0
# FastVideo helpers retained for H3. Origins and modifications: docs/sources.json.
"""Shared quantization, linear and embedding helpers used by H3."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from h3_apple._vendor.fastvideo_mlx.logger import init_logger

if TYPE_CHECKING:
    import mlx.core as mx

logger = init_logger(__name__)


class UnsupportedMLXQuantizationError(ValueError):
    """A quantization mode the installed MLX build cannot execute.

    Raised by :func:`ensure_quantization_supported` before any model weights
    are loaded, so callers (CLI flags, benchmark sweeps) can fail fast with an
    actionable message -- or skip the mode -- instead of crashing deep inside
    ``mx.quantize`` mid-load.
    """


@dataclass(frozen=True)
class MLXQuantizationSpec:
    """MLX quantized-matmul configuration for DiT linear weights."""

    mode: str
    bits: int | None = None
    group_size: int | None = None

    @classmethod
    def from_name(cls, name: str | None) -> MLXQuantizationSpec | None:
        if name is None or name in {"", "none", "fp16", "fp32"}:
            return None
        if name == "int8":
            return cls(mode="affine", bits=8, group_size=64)
        if name == "int6":
            return cls(mode="affine", bits=6, group_size=64)
        if name == "int4":
            return cls(mode="affine", bits=4, group_size=64)
        if name == "mxfp8":
            return cls(mode="mxfp8")
        if name == "mxfp4":
            return cls(mode="mxfp4")
        if name == "nvfp4":
            return cls(mode="nvfp4")
        raise ValueError(f"Unsupported MLX quantization mode: {name}")

    @property
    def label(self) -> str:
        if self.mode == "affine":
            return f"int{self.bits}"
        return self.mode


@dataclass(frozen=True)
class QuantizedMatrix:
    weight: mx.array
    scales: mx.array
    biases: mx.array | None
    spec: MLXQuantizationSpec
    dequantized_dtype: mx.Dtype


def weight_dtype(weight):
    if isinstance(weight, QuantizedMatrix):
        return weight.dequantized_dtype
    return weight.dtype


_QUANT_SUPPORT_CACHE: dict[tuple[str, int | None, int | None], str | None] = {}


def quantization_support_error(spec: MLXQuantizationSpec) -> str | None:
    """Probe whether the installed MLX build supports ``spec``.

    Runs a tiny ``mx.quantize`` + ``mx.quantized_matmul`` with exactly the
    arguments :func:`quantize_matrix` / :func:`linear` use, so the result
    reflects the real runtime path. The affine (int8/int4) modes are stable
    across MLX releases, but the ``mxfp8``/``mxfp4``/``nvfp4`` mode strings
    require newer MLX builds and raise otherwise. Returns ``None`` when the
    mode works, else the underlying error message. Cached per spec.
    """
    key = (spec.mode, spec.bits, spec.group_size)
    if key not in _QUANT_SUPPORT_CACHE:
        import mlx.core as mx

        try:
            probe_dim = max(spec.group_size or 0, 64)
            weight = mx.zeros((probe_dim, probe_dim), dtype=mx.float16)
            quantized = quantize_matrix(weight, spec)
            y = linear(mx.zeros((1, probe_dim), dtype=mx.float16), quantized)
            mx.eval(y)
            _QUANT_SUPPORT_CACHE[key] = None
        except Exception as exc:  # noqa: BLE001 - MLX raises varied error types per backend/version.
            _QUANT_SUPPORT_CACHE[key] = f"{type(exc).__name__}: {exc}"
    return _QUANT_SUPPORT_CACHE[key]


def ensure_quantization_supported(spec: MLXQuantizationSpec | None) -> None:
    """Raise :class:`UnsupportedMLXQuantizationError` if ``spec`` cannot run here."""
    if spec is None:
        return
    error = quantization_support_error(spec)
    if error is None:
        return
    import mlx.core as mx

    mlx_version = getattr(mx, "__version__", "unknown")
    raise UnsupportedMLXQuantizationError(f"MLX quantization mode '{spec.label}' is not supported by the installed mlx "
                                          f"({mlx_version}): {error}. Upgrade mlx or pick a supported mode "
                                          f"(int8 is currently the most reliable quality/memory target).")


def quantize_matrix(weight, spec: MLXQuantizationSpec | None):
    if spec is None:
        return weight
    import mlx.core as mx

    if len(weight.shape) < 2:
        return weight
    q = mx.quantize(weight, group_size=spec.group_size, bits=spec.bits, mode=spec.mode)
    biases = q[2] if len(q) == 3 else None
    eval_args = [q[0], q[1]]
    if biases is not None:
        eval_args.append(biases)
    mx.eval(*eval_args)
    return QuantizedMatrix(
        weight=q[0],
        scales=q[1],
        biases=biases,
        spec=spec,
        dequantized_dtype=weight.dtype,
    )


_AFFINE_DQ_GEMM_BITS = frozenset({2, 3, 4, 5, 6, 8})


MLX_AFFINE_DQ_GEMM_DEFAULT_MIN_M = 768


_dq_gemm_engaged = 0


_dq_gemm_logged = False


def affine_dq_gemm_min_m() -> int | None:
    raw = os.environ.get("FASTVIDEO_MLX_DQ_GEMM", "1").strip().lower()
    if raw in {"", "0", "off", "false", "no"}:
        return None
    if raw in {"1", "on", "true", "yes"}:
        return MLX_AFFINE_DQ_GEMM_DEFAULT_MIN_M
    try:
        value = int(raw)
    except ValueError:
        return MLX_AFFINE_DQ_GEMM_DEFAULT_MIN_M
    if value <= 0:
        return None
    return value


def _matmul_leading_rows(x) -> int:
    last = int(x.shape[-1]) if x.ndim else 0
    if last <= 0:
        return 0
    return int(x.size) // last


def _quantized_linear(x, weight: QuantizedMatrix, *, use_affine_dq_gemm: bool = False):
    import mlx.core as mx

    global _dq_gemm_engaged, _dq_gemm_logged
    spec = weight.spec
    min_m = affine_dq_gemm_min_m() if use_affine_dq_gemm else None
    rows = _matmul_leading_rows(x)
    if (min_m is not None and spec.mode == "affine" and spec.bits in _AFFINE_DQ_GEMM_BITS
            and spec.group_size is not None and rows >= min_m):
        dequantized = mx.dequantize(
            weight.weight,
            weight.scales,
            weight.biases,
            group_size=spec.group_size,
            bits=spec.bits,
            mode=spec.mode,
            dtype=x.dtype,
        )
        y = (x @ dequantized.T).astype(x.dtype)
        _dq_gemm_engaged += 1
        if not _dq_gemm_logged:
            _dq_gemm_logged = True
            logger.info("affine dequant+GEMM engaged (rows=%d, floor=%d, bits=%s)", rows, min_m, spec.bits)
        return y
    return mx.quantized_matmul(
        x,
        weight.weight,
        weight.scales,
        weight.biases,
        transpose=True,
        group_size=spec.group_size,
        bits=spec.bits,
        mode=spec.mode,
    ).astype(x.dtype)


def linear(x, weight, bias=None, *, use_affine_dq_gemm: bool = False):
    y = (_quantized_linear(x, weight, use_affine_dq_gemm=use_affine_dq_gemm)
         if isinstance(weight, QuantizedMatrix) else x @ weight.T)
    if bias is not None:
        y = y + bias
    return y


def silu(x):
    import mlx.core as mx

    return x * mx.sigmoid(x)


def timestep_embedding(t, dim: int, max_period: int = 10000):
    import mlx.core as mx

    half = dim // 2
    freqs = mx.exp(-math.log(max_period) * mx.arange(0, half, dtype=mx.float32) / half)
    args = t[:, None].astype(mx.float32) * freqs[None]
    embedding = mx.concatenate([mx.cos(args), mx.sin(args)], axis=-1)
    if dim % 2:
        embedding = mx.concatenate([embedding, mx.zeros_like(embedding[:, :1])], axis=-1)
    return embedding
