"""Private diagnostic: PEFT-style unfused BF16 LoRA on the existing MLX DiT."""
from contextlib import contextmanager


@contextmanager
def runtime_peft(dit, adapter_path):
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
        tensors[edit['lora_A.weight']].astype(mx.bfloat16),
        tensors[edit['lora_B.weight']].astype(mx.bfloat16),
    ) for name, edit in plan.items()}
    mx.eval([x for pair in pairs.values() for x in pair])
    original = h3.linear
    receipt = dict(modules=len(pairs), adapted_calls=0)

    def linear(value, weight, bias=None):
        if id(weight) not in pairs:
            return original(value, weight, bias)
        if bias is not None or value.dtype != mx.bfloat16 or weight.dtype != mx.bfloat16:
            raise ValueError('Expected bias-free BF16 adapted projections')
        a, b = pairs[id(weight)]
        base = original(value, weight)
        down = (value @ a.T).astype(mx.bfloat16)
        up = (down @ b.T).astype(mx.bfloat16)
        delta = (up * (8 / 128)).astype(mx.bfloat16)
        receipt['adapted_calls'] += 1
        return (base + delta).astype(mx.bfloat16)

    h3.linear = linear
    try:
        yield receipt
    finally:
        h3.linear = original
