# Development

## Runtime

| Mode | Entry | Implementation |
| --- | --- | --- |
| VSA, default | `runtime/engine.py` | Vendored MLX; W8A8 projections, shared QKV activation packing, INT8 QK |
| SOL | `engine.py` | Native vpipe; INT8 GEMM, SOL and Sage attention |

Both use the original LightX2V four-step adapter. SOL merges it into BF16 weights
in FP32, rounds to BF16, then quantizes to W8G64. Manifests bind this recipe;
runtime reapplication is rejected. The formats are separate, with no silent fallback.

The Python facade owns validation, preparation, resource limits, progress,
cancellation, media checks and run records. Workers isolate optional dependencies.
VSA conversion runs separately; SOL without X2 needs no MLX or PyTorch.

`runtime/dispatch.py` fixes VSA arithmetic. Reference preprocessing uses sampling
area and 32-pixel alignment. Native 768p is center-cropped; extra frames are
trimmed with sample-accurate audio endpoints.

[Contribution map](releases/0.7.0.md#what-comes-from-the-community-and-what-we-contributed) ·
[File origins](sources.json) · [Model sources](../src/h3_apple/data/model-sources.json) ·
[VSA gates](../src/h3_apple/data/vsa-gates.json) · [Notices](../THIRD_PARTY_NOTICES)

## Verify a change

```bash
conda create --prefix .local/envs/h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
.local/envs/h3/bin/python -m pip install -r environments/dev.lock
.local/envs/h3/bin/python -m pip install --no-build-isolation ".[VSA,faces]"
.local/envs/h3/bin/python -I -m pytest tests -q
```

SOL-only environments can use `-m "not hardware"`; optional tests skip when their
dependencies are absent. Hardware tests compare real M5 kernels with independent
numerical oracles. Tests use temporary inputs, not previous experiments.

Release checks also require a clean wheel install, model preparation or verified
reuse, and complete CLI/API videos. Execution, quality and speed are separate claims.

## Optional X2 decoder

`runtime/x2_vae.py` serves both modes. SOL supplies normalized latents and original
audio to an isolated MLX worker. Sampling and delivery dimensions stay separate;
reference budgets follow sampling. Validation rejects 768p + X2 before setup.

Tests cover both modes/orientations, RGB packing and native-768p cropping.
Run the large-array temporal-copy regression with:

```sh
H3_TEST_LARGE_ARRAYS=1 .local/envs/h3/bin/python -m pytest tests/test_vae_chunks.py
```

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

## Optional restoration

`faces/` uses a separate worker and the shared GPU lock. Keep its pinned manifests,
component notices and vendored inference subset. Avoid dynamic Torch Hub downloads,
training dependencies and research-directory imports.

Two decode passes bound frame memory; temporary PNGs support exact pre-encode
comparison. Release checks cover both entry points, audio preservation, no-face
copying, cancellation, cuts, timing and existing-file protection.
See [restoration behavior and terms](face-enhancement.md).

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
