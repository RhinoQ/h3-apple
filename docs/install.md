# Installation

The recommended installation uses a dedicated Conda environment on an Apple
Silicon Mac. Use your existing Conda installation, or install the Apple Silicon
version of [Miniforge](https://github.com/conda-forge/miniforge) first:

```bash
conda create -n h3 -c conda-forge python=3.11 pip -y
conda activate h3
python -m pip install h3-apple
h3 generate --image reference.jpg --prompt "Your scene, movement and sound."
```

Conda isolates Python and the dependencies from your other projects. pip installs
and upgrades h3-apple inside that environment. Activate it in each new terminal:

```bash
conda activate h3
```

`python -m h3_apple` is equivalent to `h3` and works when the scripts directory
is not on PATH. The package also exposes `import h3_apple`; both entry points
share the same first-run preparation and generation code.

Python 3.11–3.14 is supported. The package also works in an existing isolated
Python environment; Conda is the documented default, not a runtime dependency.

pip installs Pillow, PyAV and imageio-ffmpeg into the active environment. A wheel
can contain native executables and shared libraries as well as Python code:
`imageio-ffmpeg` supplies the FFmpeg executable for final video processing, while
`av` (PyAV) supplies FFmpeg 8 libraries used by the inference engine and media
validation. h3 resolves those packaged paths directly. A global `ffmpeg` command
on PATH is not required. No Homebrew, separate FFmpeg installation, compiler,
Xcode, PyTorch, Transformers or MLX Python package is needed.
The inference engine is downloaded on first use, checked by SHA256 and cached
under `~/.cache/h3-apple/engines`. Models are never bundled into the pip package
or downloaded during installation or import.

## First generation

`h3 generate` automatically checks the Mac, reuses or downloads model files,
prepares them, then generates your video. There is no required setup command.

The pinned MiniMax Ref2VA model and DARE/TIES adapter need approximately
**145 GB of downloads and 233 GB of free disk** for a fresh preparation.
Source files remain cached for reuse; their combined footprint with prepared
models is approximately 218 GB. The prepared model alone is about 85 GB.
The transformer and text encoder are converted to 8-bit group-64 weights.
These are disk sizes, not peak runtime memory.

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

Models default to `~/Models/h3-apple/ref2va`. To use another volume:

```bash
export H3_MODEL_DIR=/Volumes/Models/h3-apple
h3 generate --image reference.jpg --prompt "Your scene"
```

Keep the variable set for subsequent runs, or pass `--model-dir` / `model_dir`
explicitly. Existing registered native Ref2VA installations from h3-apple 0.3
are automatically detected under `~/Models`. Existing 0.4 prepared models
continue to work. Files are verified and hard-linked on the same volume;
cross-volume reuse makes verified copies. Existing models are not deleted.

For a custom source snapshot or another prepared model directory:

```bash
h3 prepare --reuse-dir /path/to/models
```

`h3 prepare` remains an optional way to prepare in advance. Old MLX-converted
bundles cannot substitute for native weights. Sources, revisions and SHA256
hashes are in [model-sources.json](../src/h3_apple/data/model-sources.json).
Model license terms still apply.

## Troubleshooting

`h3 doctor` checks hardware, pip-provided media tools, the engine and model
receipts. Before first generation it may report that models are not yet ready.
`h3 verify` performs a full weight checksum pass. To upgrade:

```bash
python -m pip install --upgrade h3-apple
```

An M5 Mac with macOS 26.2+ and at least 64 GB unified memory is required.
Other Apple Silicon generations have not been qualified. Use 576p on a 64 GB
machine; 768p beyond 5 seconds requires 96 GB. Generation stops if swap grows
by more than 2 GiB or macOS reports serious thermal pressure. It reserves
20 GiB of free disk for temporary media. Failed jobs retain their logs.
