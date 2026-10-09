# Development

h3-apple exposes still-image Ref2VA with four denoising forwards through two
modes. SOL uses the native INT8 GEMM, SOL attention and SageAttention engine.
VSA uses the vendored MLX runtime with W8A8 projections, direct BF16 output,
consecutive QKV activation reuse and INT8 QK inside VSA. Both use the original
LightX2V four-step adapter. SOL prepares it by FP32 merging into original BF16
weights, BF16 rounding, then W8G64 quantization. The prepared config and manifest
record that identity; generation must not apply the adapter a second time.
Prompt and reference ordering are preserved.
Image preprocessing uses the sampling canvas area and 32-pixel alignment. The
768p model canvas is center-cropped and extra frames trimmed with sample-accurate
audio endpoints.

The shared Python facade owns input validation, preparation, resource limits,
progress, cancellation, media validation and run records. `engine.py` owns SOL
execution; `runtime/engine.py` owns VSA execution. Each has one implementation
and its own verified model format. VSA is the default; there is no silent
mode or attention fallback. `vsa_preparation.py` reuses the source downloader
and launches the converter in an isolated process. VSA imports stay inside its
worker so a SOL-only installation does not need MLX or PyTorch.

The adopted VSA arithmetic is fixed in `runtime/dispatch.py`. Research variants
and environment switches are not exposed. The frozen kernel names retain their
provenance. See [sources.json](sources.json) and the adjacent Metal notices.

The engine builds on [vpipe at the pinned commit](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057)
with the [native patches](../tools/engine-patches/README.md).
Its authors and dependencies are credited in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES).
Published releases download and manage their pinned engine internally. The source
checkout currently pins an unpublished local artifact, built as described below.

## Verify a change

Development uses a project-local Conda environment. Users are also guided to use
Conda for Python and FFmpeg, with pip managing h3-apple and Pillow inside it.

```bash
conda create --prefix .local/envs/h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
.local/envs/h3/bin/python -m pip install -r environments/dev.lock
.local/envs/h3/bin/python -m pip install --no-build-isolation ".[VSA,faces]"
.local/envs/h3/bin/python -I -m pytest tests -q
```

For a SOL-only environment, use `-m "not hardware"`; optional VSA and face
tests skip when their dependencies are absent. Hardware tests exercise the
real M5 integer kernels against independent numerical oracles.

Tests use temporary files and synthetic media. A release also needs a normal
wheel installation, an actual model preparation or verified local reuse,
and a complete image-reference video through both public entry points. Keep execution,
quality judgments and performance comparisons as separate claims.

## Optional X2 decoder

`runtime/x2_vae.py` supplies the X2 decoder for both sampling modes when `x2=True`.
SOL exports normalized latent data and original audio to an isolated X2 worker.
The facade keeps sampling and delivery dimensions separate; reference budgets
follow sampling. Tests cover both orientations, RGB packing and alignment crop.
Run `H3_TEST_LARGE_ARRAYS=1 python -m pytest tests/test_vae_chunks.py` to include
the 2.56 GB temporal-copy regression. New integration evidence must distinguish
ordinary-path reproducibility from X2 quality and performance claims.

## Build the engine artifact

Check out the exact source revision above, including its submodules, and apply
`tools/engine-patches/stable-compute.patch`, then
`tools/engine-patches/vae-fusion.patch`, then `tools/engine-patches/vae-int8.patch`.
For this checkout, additionally apply `rope-precision.patch`, `bf16-premerge.patch`
and `premerge-quantize.patch` from that directory, in that order. Build
against FFmpeg 8 headers in a separate build environment, in Release mode:

```bash
conda create --prefix .local/envs/engine-build -c conda-forge ffmpeg=8.1.2
cmake -S /path/to/vpipe -B /path/to/build -DCMAKE_BUILD_TYPE=Release \
  -DVPIPE_METAL_RUNTIME_COMPILE=ON \
  -DVPIPE_FFMPEG_INCLUDE_DIRS="$PWD/.local/envs/engine-build/include"
cmake --build /path/to/build --target vpipe vpipe-cli -j 8
.local/envs/h3/bin/python tools/package_engine.py \
  --source-dir /path/to/vpipe --build-dir /path/to/build \
  --output /path/to/h3-apple-engine-macos-arm64.zip --local-only \
  --capability stable-compute-v1 --capability vae-fusion-v1 \
  --capability vae-h256-int8-v1 --capability h3-premerge-quantize-v1
```

Follow upstream build requirements for CMake and platform tools. Metal sources
are embedded in the library and compiled at runtime. The release CLI and library
link only to system libraries; at runtime FFmpeg 8 is loaded from the running
Python environment’s `lib` directory.
The local packager installs the archive in the download cache and updates the
source manifest, so build the wheel after packaging. The artifact carries
upstream licenses and notices. `data/engine.json` pins the
archive and every member by size and SHA256. Build identity is recorded, but
byte-identical compiler output across SDK versions is not promised.

Release source and wheel must contain identical Python/data files. The pinned
engine artifact is reused until its implementation changes. Do not bundle model
weights or user reference images in release assets.

## Optional restoration

`faces/` is a separate worker path, sharing the generation device lock. It does
not import PyTorch into the caller. Install the `faces` extra to run its full
tests; the core environment skips tests requiring those optional packages.
Keep the fixed model manifest and component notices with the vendored inference
subset. Do not reintroduce dynamic Torch Hub downloads, research-directory
imports or training dependencies. Two decoding passes bound image memory to one
frame; temporary PNGs support exact pre-encode replay and are removed after a
successful ordinary run. See [the public contract](face-enhancement.md).

An enhancement release must exercise both public entry points, verify source
audio and no-face copying, and compare installed pre-encode output against the
accepted fixed recipe. Tests for cancellation, existing files, cuts and input
timing are independent of subjective quality evaluation. Model setup is
verified separately from processing time.

## Publish the Python package

Build an sdist and wheel with `python -m build`, then check them with
`python -m twine check dist/*`. Verify installation from the wheel in a clean
Conda environment containing Python and FFmpeg, and test the documented CLI and
Python calls against real models before publishing a release.

The `publish.yml` workflow builds and checks the package on a version tag.
PyPI publication uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/):
run the workflow manually against that tag with `publish_to_pypi` enabled after
registering the publisher. Until then, users install the GitHub release wheel.
Register the GitHub owner `RhinoQ`, repository `h3-apple`, workflow `publish.yml`
and environment `pypi` in the PyPI project's publishing settings (or as a pending
publisher before the first release). This links the maintainer's PyPI account
without storing a long-lived API token in the repository. Uploads require a
tag whose version matches both the project metadata and the Python package.
