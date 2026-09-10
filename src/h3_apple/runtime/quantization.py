"""Fixed integer primitives and FP16 projections; licenses in metal/."""
import hashlib
from pathlib import Path

import mlx.core as mx

HERE = Path(__file__).resolve().parent
TEXT = (HERE / "metal/p087_h3c.metal").read_text()
assert (
    hashlib.sha256(TEXT.encode()).hexdigest()
    == "6821dcdb23a4c5a5bef8d25c023cc1e264283b9740df2834844ff6196eaae160"
)
HEADER = """#include <metal_stdlib>
#include <metal_tensor>
#include <MetalPerformancePrimitives/MetalPerformancePrimitives.h>
using namespace metal;
using namespace mpp::tensor_ops;
struct linear_args { uint rows; uint input_dim; uint output_dim; uint has_bias; };
"""
HEADER += TEXT[
    TEXT.index("inline uint h3_compact_morton_even_bits") : TEXT.index(
        "inline float h3_int8_reduce_max("
    )
]


def kernel_body(name):
    start = TEXT.index("kernel void " + name + "(")
    start = TEXT.index("{", start)
    depth = 1
    end = start + 1
    while depth:
        depth += (TEXT[end] == "{") - (TEXT[end] == "}")
        end += 1
    return TEXT[start + 1 : end - 1]


def quantize(x, group):
    xf = x.astype(mx.float32).reshape(x.shape[0], -1, group)
    maximum = mx.max(mx.abs(xf), axis=-1, keepdims=True)
    scales = mx.where(maximum > 0, maximum / 127.0, 1.0 / 127.0)
    inverse = mx.where(maximum > 0, 127.0 / maximum, 127.0)
    q = mx.clip(mx.round(xf * inverse), -127, 127).astype(mx.int8)
    return q.reshape(x.shape), scales.squeeze(-1)

start = TEXT.index("inline float h3_int8_reduce_max(")
brace = TEXT.index("{", start)
depth = 1
end = brace + 1
while depth:
    depth += (TEXT[end] == "{") - (TEXT[end] == "}")
    end += 1
QHEADER = (
    HEADER
    + TEXT[start:end]
    + """
struct int8_quant_args {uint rows; uint columns; float clip;};
struct int8_group_quant_args {uint rows; uint columns; uint group_size; uint groups;};
"""
)


def linear_fp16(x, weight, bias=None):
    import mlx.core as mx

    if (
        x.dtype != mx.float32
        or weight.dtype not in (mx.float32, mx.float16)
        or (bias is not None and bias.dtype != mx.float32)
    ):
        raise ValueError("linear requires FP32 activation/bias and FP32 or prepared FP16 weight")
    if (
        x.ndim < 2
        or weight.ndim != 2
        or x.shape[-1] != weight.shape[1]
        or min(weight.shape) <= 0
        or (bias is not None and bias.shape != (weight.shape[0],))
    ):
        raise ValueError("incompatible linear shape")
    # astype on an already FP16 array is a no-op, not another weight conversion.
    result = (x.astype(mx.float16) @ weight.astype(mx.float16).T).astype(mx.float32)
    return result + bias if bias is not None else result
