# Native compute policy and VAE

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
