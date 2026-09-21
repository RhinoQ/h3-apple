# Installation

Run `./install.sh` from the release source folder. It uses an existing Conda
installation, or bootstraps a pinned Miniforge under `.local/miniforge`.
The project environment lives in `.local/envs/h3`. System Python is not modified.
Run commands through `./h3`; activating the environment is optional.

Only Pillow is needed by the Python runtime. Python, FFmpeg, Pillow and the
native engine are pinned. The engine is downloaded automatically from the
same release, checked by SHA256 and installed in `~/.cache/h3-apple/engines`.
No compiler, Xcode, PyTorch, Transformers or MLX Python package is required.

## Models

The default location is `~/Models/h3-apple/ref2va`. To use another volume,
set this before installing and keep it set when generating:

```bash
export H3_MODEL_DIR=/Volumes/Models/h3-apple
./install.sh
```

Model preparation uses the pinned MiniMax Ref2VA base and DARE/TIES four-step
adapter. It converts the transformer and text encoder to 8-bit group-64
weights automatically. Model sources, revisions, sizes and SHA256 hashes are
in [model-sources.json](../src/h3_apple/data/model-sources.json).
Weights remain subject to their model licenses.

A fresh preparation downloads approximately 145 GB. Source files remain
cached for reuse; the combined source and converted footprint is approximately
218 GB, with additional temporary headroom during preparation. The prepared
model alone is about 85 GB. These are disk sizes, not peak runtime memory.

The installer asks for confirmation before downloads over 20 GB. For a
noninteractive installation, it stops before the model download; then inspect
and explicitly confirm the plan:

```bash
./h3 prepare --plan
./h3 prepare --allow-large-download
```

Downloads resume from verified partial files. Run `./h3 prepare` again after
an interruption. Failed preparation logs remain beside the model directory.
A successful source cache is retained; the installer does not delete your
existing models or research files.

To reuse a local source snapshot or an earlier compatible H3 installation:

```bash
./h3 prepare --reuse-dir /path/to/models
```

The existing registered native Ref2VA installations from h3-apple 0.3 are
automatically detected under `~/Models` when no explicit reuse directory is
provided. Weights are checked before reuse and linked into an independent
model directory on the same volume; cross-volume reuse makes verified copies.
Old MLX-converted bundles cannot substitute for these native weights.

## Troubleshooting

`./h3 doctor` checks hardware, the engine, media tools and model receipts.
`./h3 verify` performs a full weight checksum pass. An explicit `--model-dir`
overrides `H3_MODEL_DIR` for either command and for generation.

An M5 GPU is required for the integrated accelerated kernels. Other Apple
Silicon generations have not been qualified. Use 576p on a 64 GB machine;
768p beyond 5 seconds requires 96 GB. Generation stops if swap grows by more
than 2 GiB or macOS reports serious thermal pressure. It reserves 20 GiB of
free disk for temporary media. Failed jobs retain their workspace and logs.
