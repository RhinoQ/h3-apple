# Development

## Runtime

| Mode | Entry | Implementation |
| --- | --- | --- |
| VSA | `runtime/engine.py` | Vendored MLX; W8A8 projections, shared QKV activation packing, INT8 QK |
| Dense (high quality) | `runtime/engine.py` | Same VSA model bundle and W8A8 projections; BF16 full SDPA, sparse routing and gates bypassed |
| SOL, default | `engine.py` | Native vpipe; INT8 GEMM, SOL and Sage attention |

Both use the original LightX2V four-step adapter. SOL merges it into BF16 weights
in FP32, rounds to BF16, then quantizes to W8G64. Manifests bind this recipe;
runtime reapplication is rejected. The formats are separate, with no silent fallback.

The Python facade owns validation, preparation, resource limits, progress,
cancellation, media checks and run records. Workers isolate inference dependencies.
VSA conversion runs separately. Installation includes both modes and X2.

`runtime/dispatch.py` fixes VSA arithmetic. Reference preprocessing uses sampling
area and 32-pixel alignment. Native 768p is center-cropped; extra frames are
trimmed with sample-accurate audio endpoints.

[Implementation and credits](#implementation-and-credits) ·
[File origins](sources.json) · [Model sources](../src/h3_apple/data/model-sources.json) ·
[VSA gates](../src/h3_apple/data/vsa-gates.json) · [Notices](../THIRD_PARTY_NOTICES)

## Verify a change

```bash
conda create --prefix .local/envs/h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
.local/envs/h3/bin/python -m pip install -r environments/dev.lock
.local/envs/h3/bin/python -m pip install --no-build-isolation "."
.local/envs/h3/bin/python -I -m pytest tests -q
```

Use `-m "not hardware"` to skip GPU tests. Hardware tests compare real M5 kernels with independent
numerical oracles. Tests use temporary inputs, not previous experiments.

Release checks also require a clean wheel install, model preparation or verified
reuse, and complete CLI/API videos. Execution, quality and speed are separate claims.

## X2 decoder

`runtime/x2_vae.py` serves both modes. SOL supplies normalized latents and original
audio to an isolated MLX worker. Sampling and delivery dimensions stay separate;
reference budgets follow sampling. Validation rejects 768p + X2 before setup.

Tests cover both modes/orientations, RGB packing and native-768p cropping.
Run the large-array temporal-copy regression with:

```sh
H3_TEST_LARGE_ARRAYS=1 .local/envs/h3/bin/python -m pytest tests/test_vae_chunks.py
```

## Implementation and credits

**New in 0.8.2:** three quality choices share the CLI/API configuration resolver.
Fast selects existing SOL 544p/X2, medium selects VSA native 768p, and high uses
Dense native 768p followed by the existing VOSR workflow. Dense uses MLX's BF16
scaled dot-product attention on the inherited H3 full-attention branch. The
four-step weights and projection arithmetic are unchanged; runtime counters
verify 200 Dense blocks and zero sparse calls. Durations remain 5–15 seconds
at whole 24 fps frames. This does not imply uniform quality improvements.

**New in 0.8.1:** VOSR accepts H3 X2 output in either orientation. For these larger
inputs, VAE attention processes 2,048 queries at a time against the complete key
and value tensors. This bounds temporary memory without spatial VAE tiles.
Native inputs retain their existing execution and fixed noise. New sizes use
deterministic CPU noise, with its checksum recorded for replay.

**New in 0.8.0:** full-video VOSR restoration through `upscale()` and `h3 upscale`.
The worker uses PyTorch 2.14.1 native FP16 attention, fused RMSNorm and resident
FP16 DINO/DiT projections; VAE precision is scoped and tile submission is
nonblocking. Sensitive normalization boundaries, blending and color processing
remain FP32. Fixed noise preserves the qualified output across the Torch upgrade.

VOSR supplies model definitions, conditioning and tiling; PyTorch supplies the
GPU kernels. Our work covers the Mac precision/execution policy, model preparation,
video/audio handling and validation. [File origins](evidence/v0.8.0-source-components.json)
and [component terms](../THIRD_PARTY_NOTICES) include the inherited noncommercial
DiT code. Models download separately.

**New in 0.7.0:** MLX X2 integration, SOL preparation/guards and the fixes below.
VSA kernel work shipped in 0.6.0. H3, VSA, SOL, SageAttention, Turbo, rotated INT8
quantization and X2 originate upstream. The table distinguishes reused code,
algorithm references and independently written integration.

| Component | Upstream | h3-apple |
| --- | --- | --- |
| Base model and Turbo | [MiniMax H3](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86); [LightX2V Ref2VA Turbo](https://huggingface.co/lightx2v/Minimax-h3-Turbo/tree/ec01fa4c86263832faa0bd1d6d8f36a281eaabb2), original **4-step v0.1** | Content-pinned preparation, compatible model manifests and explicit migration. |
| VSA runtime | Selected MLX code from [FastVideo](https://github.com/hao-ai-lab/FastVideo/tree/7bb76b5ec99807a66aa3047b901f15019abe0f00), Apache-2.0 | Ref2VA worker integration, preparation, fixed compute dispatch, delivery and reproducible source records. File-level origins/modifications are in the [source inventory](sources.json). |
| VSA gates/routing | [Kablex Ref2VA-VSA](https://github.com/Kablex/ComfyUI-Ref2VA-VSA/blob/92e3f8357c626f63cfe3813ec914f2cf3fbc500c/nodes.py): gate-only transplant and dense-exempt reference prefix; [Comfy Kitchen](https://github.com/Comfy-Org/comfy-kitchen/blob/62c5bb4a5f2f818d4be7e2a51f83aaf1286a1243/comfy_kitchen/backends/eager/sol_attn.py): routing semantics | Mac implementation and validation of prefix offsets, valid-key masks, padded lanes, tie retention and local routing. Only 50 FastH3 gate matrices are used; its T2VA deltas are not applied. |
| VSA sparse Metal attention | MLX / [mlx-flashattention-steel](https://github.com/marcogva-hub/mlx-flashattention-steel/tree/b1e7ac2586fde9e28412d81b62540f0bff281771) / MFA (MIT), Draw Things (BSD-3-Clause); retained [kernel notice](../src/h3_apple/runtime/metal/p085_NOTICE.txt) is authoritative | Selected-route traversal, reference-prefix handling and shape/mask adaptation with independent numerical checks. |
| VSA W8A8 projections | [vpipe](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057) unsigned Metal MMA GEMM and affine compensation, Apache-2.0 | MLX address-space integration, direct BF16 output, consecutive QKV **activation-pack reuse**, dispatch records and tests. Q/K/V projections remain separate and share packed input data. See the [integer-kernel source and changes](../src/h3_apple/runtime/metal/p139_NOTICE.txt). |
| VSA INT8 QK | [SageAttention2](https://arxiv.org/abs/2411.10958), smoothing/mean-restoration idea | Independently written MLX/Metal centered per-token INT8 QK using the paper's smoothing and mean-restoration idea. Local tests and benchmarks establish Mac correctness and performance. |
| SOL engine | [vpipe](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057), T-Go LLC, Apache-2.0: native inference, INT8 GEMM, SOL and Sage attention | Python product wrapper, fixed compute policy, strict replay and allocation checks, RoPE correction following [upstream](https://github.com/tgo-app-dev/vpipe/commit/8ffe228d54d7), and BF16 Turbo premerge before quantization with compatibility/double-application guards. Native SOL/Sage remains upstream code. |
| Ordinary VAE | vpipe native decoder; [h3.c](https://github.com/antirez/h3.c/tree/8974cc055ea9c02fcd14cc27dfda3e1027c05153) kernels (MIT); Comfy Kitchen H256/ConvRot INT8 idea | Native fusion preserves explicit BF16 round points; local Metal H256 W8A8 linear implementation and bounded temporal copy. These INT8 choices apply to ordinary VAE decoding. |
| X2 | [MiniMax H3 X2 Detail VAE](https://huggingface.co/speach1sdef178/MiniMax-H3-X2-Detail-VAE/tree/af8c92d267c6849fec5032c35a65d5766737b338) weights/reference design, MiniMax terms and author NOTICE; [ComfyUI-H3-X2-Stream](https://github.com/sepiablue-ai/ComfyUI-H3-X2-Stream/tree/eb148a3d0f91a273668bbe027bfcbafb85f2c5e8) architectural reference | Independent MLX decoder/key mapping/RGB PixelShuffle integration on the inherited H3 VAE core; sampling-vs-delivery dimensions, SOL normalized-latent bridge, audio preservation and portrait/landscape interfaces. No GPL ComfyUI runtime, CUDA, NVENC or ConvRot code from Stream is copied. B32 source-image enhancement is not used. |


[Notices](../THIRD_PARTY_NOTICES), [file origins](sources.json), model manifests
and kernel notices retain exact authorship and licenses. Original integration is
Apache-2.0; third-party code and models keep their own terms.

### Correctness details

- **SOL preparation:** merge Turbo in FP32, round to BF16, then quantize to
  W8G64. This removed duplicate subjects in the regression and two fresh cases.
  The controlled integration pair was 7.15% slower; the change improves
  correctness. [Evidence](evidence/sol-premerge-source.json).
- **X2 color grids:** MLX 0.32.0 overflowed 32-bit offsets when copying temporal
  views of a 2,562,195,456-element array. Final concatenation uses the CPU above
  the signed-32-bit limit; decoding stays on GPU.
  [Copy and long-clip checks](evidence/v0.7.0-x2-grid-fix.json).
- **Geometry and cancellation:** preserve native-768p cropping and X2 dimensions;
  tolerate worker groups that have already exited while surfacing permission
  errors for live processes. The green borders seen in early previews were CSS.

## Build the engine artifact

Start from [vpipe `f34e2cc`](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057),
including submodules. Apply [these patches](../tools/engine-patches/README.md) in order:

1. `stable-compute.patch`
2. `vae-fusion.patch`
3. `vae-int8.patch`
4. `rope-precision.patch`
5. `bf16-premerge.patch`
6. `premerge-quantize.patch`

Build in Release mode with FFmpeg 8 headers and upstream CMake/platform tools:

```bash
conda create --prefix .local/envs/engine-build -c conda-forge ffmpeg=8.1.2
cmake -S /path/to/vpipe -B /path/to/build -DCMAKE_BUILD_TYPE=Release \
  -DVPIPE_METAL_RUNTIME_COMPILE=ON \
  -DVPIPE_FFMPEG_INCLUDE_DIRS="$PWD/.local/envs/engine-build/include"
cmake --build /path/to/build --target vpipe vpipe-cli -j 8
.local/envs/h3/bin/python tools/package_engine.py \
  --source-dir /path/to/vpipe --build-dir /path/to/build \
  --output /path/to/h3-apple-engine-macos-arm64.zip --local-only \
  --capability stable-compute-v1 \
  --capability vae-h256-int8-v1 --capability h3-premerge-quantize-v1
```

Metal sources compile at runtime. FFmpeg loads from the active Python environment's
`lib`; the CLI/library link only to system libraries.

Packaging caches the archive and updates `data/engine.json`, which pins every
member by size and SHA256. Build the wheel afterward. Use `--url HTTPS_URL`
instead of `--local-only` for a published artifact; packaging itself does not publish.
Build identities are recorded; byte-identical output across SDKs is not promised.

## Publish the Python package

Build and check using the project environment:

```sh
.local/envs/h3/bin/python -m build
.local/envs/h3/bin/python -m twine check dist/*
```

Source and wheel must contain identical Python/data files. Verify a clean wheel
install and real CLI/API generation. Reuse the qualified engine until its code
changes; never bundle weights or user references.

A version tag triggers `publish.yml`: distributions, engine verification, then
a GitHub Release containing the wheel, sdist, engine, Ref2VA skill, manifest and
checksums. Notes come from `docs/releases/<version>.md`; links target that tag.

For PyPI, configure [Trusted Publishing](https://docs.pypi.org/trusted-publishers/)
with owner `RhinoQ`, repository `h3-apple`, workflow `publish.yml`, environment
`pypi`. Run that tag's workflow with `publish_to_pypi` enabled. Tag, package and
project versions must agree. Until configured, install the GitHub release wheel.
