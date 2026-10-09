"""Private numerical diagnostic for the existing MLX H3 forward.

Not an inference backend or a supported product recipe. It reuses the product's
loader, layout conversion and transformer; only the low-rank linear addition is
substituted. No merged or quantized checkpoint is written.
"""
from contextlib import contextmanager


@contextmanager
def runtime_lora(dit, adapter_path):
    """Match the native separate-LoRA BF16 stores on original base matrices."""
    import mlx.core as mx
    from h3_apple._vendor.fastvideo_mlx import minimax_h3 as h3
    from h3_apple.vsa_conversion import header, ref2va_adapter_plan

    modules = [(f"transformer_blocks.{i}.", block) for i, block in enumerate(dit.blocks)]
    modules += [(f"token_refiner.refiner_blocks.{i}.", block) for i, block in enumerate(dit.refiner)]
    weights = {prefix + name: value for prefix, block in modules for name, value in block.items()
               if value is not None}
    plan = ref2va_adapter_plan(header(adapter_path), {k: v.shape for k, v in weights.items()})
    tensors = mx.load(str(adapter_path))
    pairs = {id(weights[name]): (
        (tensors[edit['lora_A.weight']].astype(mx.float32) * (8 / 128)).astype(mx.bfloat16),
        tensors[edit['lora_B.weight']].astype(mx.bfloat16),
    ) for name, edit in plan.items()}
    mx.eval([x for pair in pairs.values() for x in pair])
    original = h3.linear
    receipt = dict(modules=len(pairs), adapted_calls=0)

    def linear(value, weight, bias=None):
        if id(weight) not in pairs:
            return original(value, weight, bias)
        if bias is not None or value.dtype != mx.bfloat16 or weight.dtype != mx.bfloat16:
            raise ValueError("The diagnostic requires bias-free BF16 adapted projections")
        a, b = pairs[id(weight)]
        base = original(value, weight)
        down = (value @ a.T).astype(mx.bfloat16)
        # Native B accumulates in FP32 into the already stored BF16 base result,
        # then stores BF16 once. Keep that boundary explicit.
        result = mx.addmm(base.astype(mx.float32), down.astype(mx.float32),
                         b.astype(mx.float32).T).astype(mx.bfloat16)
        receipt['adapted_calls'] += 1
        return result

    h3.linear = linear
    try:
        yield receipt
    finally:
        h3.linear = original
