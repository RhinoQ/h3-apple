# Experimental native image-reference generation

This candidate adds a low-level, single-image Ref2VA route. It combines the
dedicated MiniMax Ref2VA transformer, LightX2V Ref2V Turbo v0.1 (rank 128,
alpha 8), and the 50 compression gates from FastH3 VSA Data-Free. It does not
apply FastH3's T2VA low-rank or exact-delta updates.

The standard public CLI/API remains the tested text-to-audio-video interface.
Reference-image quality, video references, reference audio and multiple images
are not qualified by the existence of this candidate.

Install the candidate wheel with the `ref2va` extra for its CPU vision tower.
Use `h3_apple.conversion.convert_dit(native_transformer, ref2va_lora, output,
progress, task="ref2va", gate_source=fasth3_adapter)` to prepare a new checkpoint.
Conversion refuses an existing output directory and writes `ref2va_recipe.json`.
The gate source may be the full FastH3 adapter; only its gate tensors are applied.

For a resolved five-second request, the experimental integration is:

```python
from h3_apple.runtime.engine import run

result = run(request, assets, output_path, on_progress, diagnostics_dir,
    ref2va={
        "native_root": native_ref2va_component_root,
        "image_path": reference_image,
        "pixel_budget": 672 * 384,
        "attention": "vsa",  # "dense" uses the same checkpoint without VSA
    })
```

`assets["checkpoint"]` must point to the newly converted Ref2VA checkpoint;
`assets["components"]` supplies the H3 audio/video decoders. The native reference
root must include processor, tokenizer, Qwen vision/language and VAE encoder
assets. Both image encoders receive the same aspect-preserving RGB pixels.
The full request prompt is preserved. Only generated latent rows are decoded.

The VSA mode uses 64-token tiles, 75% nominal sparsity, independent prefix
segments and dense-exempt prefix queries/keys. Like Comfy Kitchen's Sol-Attn,
it rounds the non-sink top-k budget, preserves ties, and also keeps neighboring
tiles. Actual sparsity is recorded separately from the nominal setting. The
original FastH3 routing remains the default for text-only generation.

This route uses the Ours INT8/group64 and BF16 representation, native H3 decode,
and NumPy seed streams. It does not reproduce ComfyUI's ConvRot/NVFP4 assets or
CUDA RNG/arithmetic. Its outputs must not be described as FP32-equivalent.
Installed-wheel unit and operator tests establish structural/numerical behavior;
identity quality and end-to-end speed require their own measured results.
