"""Fixed direct selected-route NAX kernel for the optional P085 runner.

The source and license notices are in metal/p085_NOTICE.txt. This preserves
the research prototype's arithmetic, including MPP relaxed_precision=true.
The return layout includes zero prefix rows, as required by FastVideo.
"""

import math
from pathlib import Path

import numpy as np

KERNEL_NAME = "p085_direct_selected_nax_bq64_bk32"
METAL = Path(__file__).with_name("metal")


def sources():
    return tuple(
        (METAL / name).read_text() for name in ("p085_nax_header.metal", "p085_nax_body.metal")
    )


def validate_metadata(shape, route_shape, count_shape, geometry, scale):
    """CPU-only bounds before any array addressing or template specialization."""
    g = geometry
    sizes = np.asarray(g.variable_block_sizes)
    if (
        len(shape) != 3
        or shape[-1] != 128
        or shape[1] <= 0
        or g.tile_elems != 64
        or g.num_prefix_tiles < 0
        or g.num_video_tiles <= 0
    ):
        raise ValueError("requires nonempty heads/video, tile64, dim128")
    ntiles = g.num_prefix_tiles + g.num_video_tiles
    if (
        sizes.shape != (ntiles,)
        or sizes.dtype.kind not in "iu"
        or np.any(sizes < 1)
        or np.any(sizes > 64)
        or g.padded_length != ntiles * 64
        or shape[0] != g.padded_length
    ):
        raise ValueError("invalid tile lengths or padded layout")
    # Upstream's constexpr stride products and route offsets use signed int.
    # Reject overflow instead of silently widening/changing the frozen kernel.
    if math.prod(shape) > 2**31 - 1 or math.prod(route_shape) > 2**31 - 1:
        raise ValueError("signed 32-bit element/route indexing bound exceeded")
    if (
        len(route_shape) != 3
        or route_shape[:2] != (shape[1], g.num_video_tiles)
        or route_shape[-1] < 1
        or route_shape[-1] > ntiles
        or count_shape != route_shape[:2]
    ):
        raise ValueError("route/count shape mismatch")
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("scale must be finite and positive")


def validate_inputs(q, k, v, idx, num, geometry, scale):
    """Symmetric B/C admission, including actual device-side route bounds."""
    import mlx.core as mx

    validate_metadata(q.shape, idx.shape, num.shape, geometry, scale)
    if any(x.shape != q.shape or x.dtype != mx.bfloat16 for x in (q, k, v)):
        raise ValueError("Q/K/V must share a BF16 layout")
    if idx.dtype != mx.int32 or num.dtype != mx.int32:
        raise ValueError("route indices and counts must be int32")
    if not bool(mx.all((num >= 0) & (num <= idx.shape[-1])).item()):
        raise ValueError("invalid route count")
    active = mx.arange(idx.shape[-1])[None, None, :] < num[..., None]
    ntiles = geometry.num_prefix_tiles + geometry.num_video_tiles
    if not bool(mx.all((~active) | ((idx >= 0) & (idx < ntiles))).item()):
        raise ValueError("active route index is out of bounds")


def make_direct_sparse(*, inputs_prevalidated=False):
    import mlx.core as mx

    header, body = sources()
    kernel = mx.fast.metal_kernel(
        name=KERNEL_NAME,
        input_names=["Q", "K", "V", "block_idx", "block_num", "block_sizes", "scale_value"],
        output_names=["O"],
        header=header,
        source=body,
        compile_options={"math_mode": "safe"},
    )

    def sparse(q, k, v, idx, num, g, scale):
        if not inputs_prevalidated:
            validate_inputs(q, k, v, idx, num, g, scale)
        queries, keys, values = [mx.contiguous(x.transpose(1, 0, 2)) for x in (q, k, v)]
        out = kernel(
            inputs=[
                queries,
                keys,
                values,
                mx.contiguous(idx),
                mx.contiguous(num),
                mx.array(g.variable_block_sizes.astype(np.int32)),
                mx.array([scale], mx.float32),
            ],
            template=[
                ("T", mx.bfloat16),
                ("HEADS", q.shape[1]),
                ("TOKEN_COUNT", g.padded_length),
                ("PREFIX_TILE_COUNT", g.num_prefix_tiles),
                ("VIDEO_TILE_COUNT", g.num_video_tiles),
                ("K_MAX", idx.shape[-1]),
            ],
            grid=(g.num_video_tiles * 128, q.shape[1], 1),
            threadgroup=(128, 1, 1),
            output_shapes=[queries.shape],
            output_dtypes=[mx.bfloat16],
            init_value=0,
        )[0]
        return out.transpose(1, 0, 2)

    return sparse


_implementation = None
_error = None
_calls = 0


def simd_kernel_available():
    import mlx.core as mx
    return _error is None and "M5" in mx.device_info().get("device_name", "")


def simd_kernel_error():
    return _error


def disable_simd_kernel(error):
    global _error
    _error = str(error)


def simd_block_sparse(q, k, v, idx, num, geometry, scale):
    """Adopted kernel with the existing index, nonempty and finite checks."""
    import mlx.core as mx
    global _implementation, _calls
    if not simd_kernel_available():
        raise RuntimeError(_error or "The Ours sparse kernel requires an M5 GPU.")
    validate_inputs(q, k, v, idx, num, geometry, scale)
    if not bool(mx.all(num > 0).item()):
        raise ValueError("Every query tile must retain at least one key tile.")
    if _implementation is None:
        _implementation = make_direct_sparse(inputs_prevalidated=True)
    output = _implementation(q, k, v, idx, num, geometry, scale)
    mx.eval(output)
    if output.shape != q.shape or output.dtype != q.dtype:
        raise ValueError("Sparse output shape or dtype changed.")
    if not bool(mx.all(mx.isfinite(output)).item()):
        raise ValueError("Nonfinite sparse attention output.")
    _calls += 1
    return output


def sparse_calls():
    return _calls
