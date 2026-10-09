# Native compute policy and VAE

The 0.7.0 source checkout includes the patches described here in its pinned local
engine. Publication is separate; the published 0.6.0 engine has its earlier recipe.
See [release status and contributions](../../docs/releases/0.7.0.md).

`bf16-premerge.patch` is applied after the RoPE patch below. Its merge helper is
reused by the adopted preparation path. The load-time experiment remains private:
its `VPIPE_H3_PREMERGE_BF16_LORA=1` path merges the
already validated native Turbo factors into fresh BF16 projection buffers at
load, using FP32 accumulation. It rejects quantized or streamed bases, multiple
adapters and non-unit request scale. It disables runtime adapters after all
projections have merged, and refuses eviction that would reload unmerged weights.
Source checkpoints and the default path remain unchanged. The pinned Turbo
alpha/rank is an exact power-of-two factor; other adapter recipes are not
qualified. `tests/native_bf16_premerge.cc` checks scalar results, BF16 ties,
row-band tails and source preservation. Effective-weight and complete-video
qualification are separate; this is not enabled by the public product wrapper.
Temporary base tensors use uncached copies: the mapped reader retains whole-shard
Metal buffers after a tensor view is released, which would keep the replaced base
allocated beside the merged weights and exhaust the GPU allocation budget.
`tests/native_premerge_residency.cc` verifies this lifetime distinction with a
temporary 16 MiB synthetic checkpoint and the actual Metal allocation counter.

`rope-precision.patch` is included in the current 0.7.0 local engine. Apply it
after the three patches below when rebuilding that engine.
It follows [vpipe's upstream correction](https://github.com/tgo-app-dev/vpipe/commit/8ffe228d54d7)
and MiniMax/diffusers: compute rotary angles in FP32 and round the cosine/sine
table to BF16. The table storage stays FP32; attention kernels are unchanged.
`tests/native_rope_table.cc` calls the same production helper and accepts an
independent golden fixture. Table agreement is separate from video quality;
this patch does not by itself establish that duplicate-person failures are fixed.

`stable-compute.patch` applies to the vpipe revision pinned before this change,
`f34e2cc3a3adae759eea254419f436f5b7800057`. It adds checked H3 QMM replay,
deterministic VAE shape selection, actual dispatch records and strict allocation
failure handling. It does not change Metal kernels, weights or attention math.

Apply it before following the native build instructions in `docs/development.md`.
The wrapper supplies the versioned policy internally and records it for every
generation, including when diagnostics are disabled. The current
policy targets the 40-core M5 Max; qualification on other GPUs is separate.

Apply `vae-fusion.patch` after `stable-compute.patch`. It keeps the decoder's
full-K FP32 accumulation, BF16 projection rounding and separate BF16 bias
rounding while combining the FFN and projection epilogues. Decoder weights,
tile geometry, overlap and attention are unchanged. The encoder uses its
existing path. The recorded native routes distinguish the fused implementation.

The native patch adds `minimax_h3_vvae_fused` GPU tests for partial row/column
tiles, guard regions and absent biases. The original path remains available
to native diagnostics for comparison; there is no new public mode or tuning
parameter. Local artifacts use `tools/package_engine.py --local-only` and the
`stable-compute-v1` / `vae-fusion-v1` capabilities. An unpublished artifact
requires the matching archive in the local cache; its URL is intentionally
unset until a release is published.

Version `0.5.1` also applies `vae-int8.patch` after those
two patches. It includes exact QK/RoPE layout fusion and an opt-in H256 rowwise
W8A8 decoder, pinned at native revision `2070ba62f5e5ef552bce65a6137638b245da6e54`.
The wrapper's `m5max-h256-int8-v1` policy requires the `vae-h256-int8-v1` engine
capability and confirms the executed integer route. The native policy for the
DiT remains `m5max-v1`. Strict replay binds both the engine and precision policy.

H256 rotation disperses channel outliers before symmetric rowwise INT8
quantization. INT32 dot products are restored with FP32 scales; projection,
bias and downstream BF16 round points remain explicit. The temporary dense
weight is released after conversion. The encoder, attention precision and
decoding geometry retain their preceding behavior. This is approximate
arithmetic and requires perceptual validation, even when numerical screens pass.
`minimax_h3_vvae_int8` tests check closed-form H256 results, integer contractions,
tail blocks, buffer guards, bias handling and nonfinite propagation.

Algorithm reference: [Comfy Kitchen ConvRot INT8 linear](https://github.com/Comfy-Org/comfy-kitchen/blob/main/comfy_kitchen/backends/cuda/ops/int8_linear.cu)
(Apache-2.0). The implementation uses native Metal MPP integer matrix operations;
Comfy's CUDA performance measurements do not predict its performance on a Mac.

Upstream behavior is retained when no product policy is supplied, for controlled
comparisons. Internal native environment controls are not public user settings.

`tests/native_compute_plan.cc` checks replay legality against the built library:
valid and repeated plans, conflicting plans, invalid shapes/splits, and a plane
budget too small for the requested split. It loads native kernels but does not
load model weights or submit GEMMs. This tests the budget contract, not operation
on a small-memory computer. From the product checkout, after the native build:

```sh
c++ -std=c++20 -O2 -mmacosx-version-min=26.0 \
  -I.local/native-source -I.local/native-source/include -I.local/native-build-01 \
  tests/native_compute_plan.cc .local/native-build-01/libvpipe.0.dylib \
  -Wl,-rpath,"$PWD/.local/native-build-01" -o .local/native-compute-plan-test
.local/native-compute-plan-test
```

`premerge-quantize.patch` is the adopted 0.7.0 preparation path, applied after
`bf16-premerge.patch`. The `model-quantize` stage accepts `h3_premerge_lora`
only for a new H3 DiT W8G64 conversion. It reuses the transformer's adapter
binder and the same FP32 merge/BF16 storage function, then runs the existing
affine quantizer. Tensors are processed individually, without a full BF16
intermediate checkpoint or an added Python ML dependency. The output marks
its adapter as merged; the H3 loader rejects runtime adapters on this output
to prevent double application. Original source tensors stay unchanged.
`tests/native_premerge_quantize.cc` constructs temporary synthetic base and
PEFT weights, compares all output tensors with independently scalar-merged
weights passed through the unmodified quantizer, and checks rejection of
already merged or quantized sources, in-place output and wrong precision.
The public source-checkout wrapper uses this preparation path and requires the exact
premerged checkpoint hashes. Its engine capability is `h3-premerge-quantize-v1`.
Older runtime-adapter model bundles require preparation in a new directory.
Local integration and publication are separate from numerical and video qualification.
