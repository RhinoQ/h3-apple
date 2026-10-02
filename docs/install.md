# Installation

The recommended installation uses a dedicated Conda environment on an Apple
Silicon Mac. Use your existing Conda installation, or install the Apple Silicon
version of [Miniforge](https://github.com/conda-forge/miniforge) first:

Install the 0.6.0 GitHub release with both generation modes:

```bash
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.6.0/h3_apple-0.6.0-py3-none-any.whl"
h3 generate --image reference.jpg --prompt "Your scene, movement and sound."
```

VSA is the default for generation, preparation and environment checks.
For SOL only, omit `[VSA]` from the installation requirement and pass `--mode SOL`
to each command (or `mode="SOL"` to the Python API). A source checkout can instead
be installed with `python -m pip install ".[VSA]"`.

Conda isolates Python and the dependencies from your other projects. pip installs
and upgrades h3-apple inside that environment. Activate it in each new terminal:

```bash
conda activate h3
```

`python -m h3_apple` is equivalent to `h3` and works when the scripts directory
is not on PATH. The package also exposes `import h3_apple`; both entry points
share the same first-run preparation and generation code.

SOL supports Python 3.11–3.14. VSA requires Python 3.11. Conda supplies Python, FFmpeg, ffprobe and the
FFmpeg shared libraries in one environment; pip installs h3-apple and Pillow; the `VSA` extra adds pinned MLX 0.32.0,
PyTorch 2.11.0, TorchVision 0.26.0, NumPy 2.4.6 and Transformers 5.14.1.
H3 uses the environment belonging to the running Python interpreter, including
in notebooks. It checks FFmpeg 8, the native library ABI, and H.264/AAC encoding
before model downloads or generation. The documented FFmpeg 8.1.2 build has been
validated with both public entry points.

To add FFmpeg to an existing H3 Conda environment:

```bash
conda activate h3
conda install -c conda-forge ffmpeg=8.1.2 -y
h3 doctor
```

SOL execution does not need Homebrew, a compiler, Xcode, PyTorch, Transformers
or the MLX Python package. VSA uses its optional Python dependencies. pip does not install Conda packages;
create the environment above before installing h3-apple.
The SOL inference engine is downloaded on first use, checked by SHA256 and cached
under `~/.cache/h3-apple/engines`. Models are never bundled into the pip package
or downloaded during installation or import.

## First generation

`h3 generate --mode SOL` or `h3 generate --mode VSA` checks the Mac, reuses or downloads model files,
prepares them, then generates your video. There is no required setup command.

For SOL, the pinned MiniMax Ref2VA model and original LightX2V Turbo adapter need approximately
**145 GB of downloads and 233 GB of free disk** for a fresh preparation.
Source files remain cached for reuse; their combined footprint with prepared
models is approximately 218 GB. The prepared model alone is about 85 GB.
The transformer and text encoder are converted to 8-bit group-64 weights.
These are disk sizes, not peak runtime memory.

VSA also uses the original LightX2V adapter, with 50 gate matrices from the
pinned FastH3 source. It retains BF16 text-encoder and FP32 VAE weights. Fresh
sources total approximately **151 GB**; the conservative setup plan reserves
about **343 GB** of additional disk for downloads, conversion and publication.
A prepared VSA bundle occupies about **111 GB** on one volume with hard links
(178 GB logical file sizes, including repeated text-encoder files). Cross-volume
copies may use the full logical size. Shared source caches reduce actual disk
and download costs; `h3 prepare --mode VSA --plan` reports the current plan.


The CLI asks before downloads over 20 GB. In scripts and the Python API,
explicit consent is required instead of a terminal prompt:

```bash
h3 prepare --plan
h3 generate --image reference.jpg --prompt "Your scene" --allow-large-download
```

In Python, review `DownloadApprovalRequired.download_bytes` and
`additional_disk_bytes`, then pass `allow_large_download=True` to `generate()`.
This is download consent, not a generation mode. Already prepared models need
no confirmation. Interrupted downloads resume when you run the command again;
checksums are verified before use.

## Model location and reuse

SOL models default to `~/Models/h3-apple/ref2va`; VSA defaults to
`~/Models/h3-apple/VSA`. `H3_MODEL_DIR` selects the SOL directory and
`H3_VSA_MODEL_DIR` selects the VSA directory. `--model-dir` / `model_dir` overrides
the selected mode's default. Use separate directories for the two formats. To use another volume:

```bash
export H3_VSA_MODEL_DIR=/Volumes/Models/h3-apple/VSA
h3 generate --image reference.jpg --prompt "Your scene"
```

Keep the variable set for subsequent runs, or pass `--model-dir` / `model_dir`
explicitly. Existing registered native Ref2VA installations from h3-apple 0.3
are automatically detected under `~/Models`. Existing 0.4–0.5.2 prepared models
are verified and reused when upgrading the adapter. Files are hard-linked on the same volume;
cross-volume reuse makes verified copies. Existing models are not deleted.

For a custom source snapshot or another prepared model directory:

```bash
h3 prepare --reuse-dir /path/to/models
```

`h3 prepare` remains an optional way to prepare in advance. A verified original
LightX2V VSA bundle from the earlier MLX implementation can be reused:

```bash
h3 prepare --mode VSA --reuse-dir /path/to/original-MLX-Ref2VA-bundle
h3 doctor --mode VSA
h3 verify --mode VSA
```

VSA verifies the adopted content hashes, including the original adapter's fused
weights and cached modulation tables. DARE/TIES bundles are rejected. Without
a prepared bundle, `--reuse-dir` can locate raw Ref2VA sources, the original
LightX2V adapter and the FastH3 gate-source file. The gate source supplies only
50 gates; its T2VA adapter deltas are excluded. Conversion runs with the same
native M5 architecture and TF32 setting as the adopted Ref2VA model.

VSA and SOL prepared bundles cannot substitute for each other. Sources, revisions and SHA256
hashes are in [model-sources.json](../src/h3_apple/data/model-sources.json) and
[VSA gate sources](../src/h3_apple/data/vsa-gates.json).
Model license terms still apply.

## Upgrading SOL models from before 0.5.3

A SOL generation or `h3 prepare --mode SOL` upgrades an existing prepared installation
to the original LightX2V Ref2VA Turbo 4-step v0.1 adapter. Only the **1.38 GB
adapter** is downloaded when the base weights and engine are already present;
the base weights are verified and are not downloaded or quantized again.
To reuse an already downloaded adapter, pass its file or directory with
`h3 prepare --mode SOL --reuse-dir /path/to/adapter.safetensors`.

The new adapter and its receipt are stored under
`<model-dir>/adapters/<adapter-sha256>/`. The original `model.json`, base weights
and adapter remain intact, so an older installed h3-apple version can still use
the same model directory. Interrupted adapter downloads are resumable. A failed
upgrade leaves the old receipt intact and can be retried with `h3 prepare --mode SOL`.

The native engine, four denoising steps, video/audio shifts (12/3) and adapter
scale (1.0) stay the same. The engine handles the adapter's alpha/rank metadata.
No additional scale adjustment is needed. This change reduces ghosting in the
tested scenes; it does not guarantee blur-free motion or exact prompt adherence.

## Troubleshooting

`h3 doctor --mode SOL` / `h3 doctor --mode VSA` checks hardware, Conda media tools and libraries, the engine and model
receipts. Before first generation it may report that models are not yet ready.
`h3 verify --mode SOL` / `h3 verify --mode VSA` performs a full weight checksum pass.
To upgrade the installed release:

```bash
python -m pip install --upgrade "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.6.0/h3_apple-0.6.0-py3-none-any.whl"
```

A 40-core M5 Max with macOS 26.2+ and at least 64 GB unified memory is required.
H3 checks this GPU configuration before preparing models; other GPU
configurations are not supported by its fixed compute policy. Existing users of
other M5 configurations should retain v0.5.0. Measurements used 128 GB; smaller
memory configurations have not been validated. The memory guard permits 576p at
64 GB; 768p beyond 5 seconds requires 96 GB. Generation stops if swap grows
by more than 2 GiB or macOS reports serious thermal pressure. It reserves
20 GiB of free disk for temporary media. Failed jobs retain their logs.

## Optional restoration

For separately installed small-face enhancement, including its additional 7.08 GB
models and component terms, see [face enhancement](face-enhancement.md).
Face enhancement is independent of the selected generation mode. Install
the release with `[VSA,faces]` for both modes and face enhancement in one environment;
the optional stacks share the tested Transformers 5.14.1 dependency.
