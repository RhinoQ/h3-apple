# Native engine patches

The 0.7.0 engine uses [vpipe `f34e2cc`](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057)
with the patches below, in order. See [build instructions](../../docs/development.md#build-the-engine-artifact)
and [source credits](../../docs/releases/0.7.0.md#what-comes-from-the-community-and-what-we-contributed).

| Patch | Purpose |
| --- | --- |
| `stable-compute.patch` | Checked QMM replay, deterministic VAE shapes, dispatch records and allocation failures; unchanged kernel math |
| `vae-fusion.patch` | Fused decoder epilogues with explicit FP32 accumulation, BF16 projection and separate BF16 bias rounding |
| `vae-int8.patch` | QK/RoPE layout fusion and H256 rowwise W8A8 ordinary-VAE decoding |
| `rope-precision.patch` | FP32 rotary angles, BF16-rounded cosine/sine, FP32 table storage |
| `bf16-premerge.patch` | Shared FP32 Turbo merge/BF16 storage helper |
| `premerge-quantize.patch` | Adopted SOL preparation: merge, BF16-round, then W8G64-quantize |

## Compute policy

The wrapper supplies and records fixed 40-core M5 Max policies:
`m5max-v1` for DiT and `m5max-h256-int8-v1` for the ordinary decoder.
Required capabilities are `stable-compute-v1`, `vae-h256-int8-v1` and
`h3-premerge-quantize-v1`. Replay binds engine and precision policy.

H256 rotation reduces channel outliers before symmetric rowwise INT8 quantization.
INT32 products use FP32 scales; BF16 projection, bias and downstream round points
remain explicit. Dense weights are released after conversion. Encoder behavior,
attention precision and decoding geometry are unchanged.

The H256 idea comes from [Comfy Kitchen ConvRot](https://github.com/Comfy-Org/comfy-kitchen/blob/main/comfy_kitchen/backends/cuda/ops/int8_linear.cu),
Apache-2.0. Local kernels use Metal integer MMA; CUDA timings do not predict Mac
speed. These approximate ordinary-VAE operations do not define X2 arithmetic.

## SOL preparation

`premerge-quantize.patch` accepts `h3_premerge_lora` only for a new H3 DiT W8G64
conversion. It reuses adapter binding and FP32 merge/BF16 storage before the
existing affine quantizer. Tensors are processed individually; original sources
stay unchanged. The loader rejects a second adapter on premerged output.
Older runtime-adapter bundles need a new preparation directory.

Temporary base tensors use uncached copies. Otherwise, mapped shard buffers can
keep replaced weights resident beside merged weights and exhaust GPU memory.

The private `VPIPE_H3_PREMERGE_BF16_LORA=1` load-time diagnostic shares the helper
but is not a public product setting. It rejects quantized/streamed bases, multiple
adapters and non-unit scale, disables runtime adapters after merging, and refuses
eviction that would reload unmerged weights. Only the pinned Turbo recipe is qualified.

RoPE follows [vpipe's correction](https://github.com/tgo-app-dev/vpipe/commit/8ffe228d54d7).
Table agreement alone does not establish video quality or fix duplicate subjects.

## Tests

| Test | Checks |
| --- | --- |
| `native_compute_plan.cc` | Replay legality, conflicting plans, shape/split limits and allocation budgets |
| `minimax_h3_vvae_fused` | Partial tiles, guards and absent biases |
| `minimax_h3_vvae_int8` | H256, integer products, tails, guards, bias and nonfinite values |
| `native_rope_table.cc` | Production helper against independent table fixtures |
| `native_bf16_premerge.cc` | Scalar results, BF16 ties, tails and source preservation |
| `native_premerge_residency.cc` | Buffer lifetime using a temporary 16 MiB checkpoint and Metal allocation counters |
| `native_premerge_quantize.cc` | All tensors against scalar merge + original quantizer; rejects merged/quantized inputs, in-place output and wrong precision |

After building the native library, run the compute-plan check from the product root:

```sh
c++ -std=c++20 -O2 -mmacosx-version-min=26.0 \
  -I.local/native-source -I.local/native-source/include -I.local/native-build-01 \
  tests/native_compute_plan.cc .local/native-build-01/libvpipe.0.dylib \
  -Wl,-rpath,"$PWD/.local/native-build-01" -o .local/native-compute-plan-test
.local/native-compute-plan-test
```

This checks the budget contract without model inference; it does not qualify
smaller-memory hardware. Numerical tests, complete-video correctness and perceptual
quality remain separate. Upstream behavior without a product policy is retained
for controlled comparisons.
