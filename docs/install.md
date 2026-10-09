# Installation

Use a dedicated Conda environment on a **40-core M5 Max with macOS 26.2+**.
The memory guard permits 64 GiB; 768p beyond five seconds requires 96 GiB.
Measurements used 128 GiB. Other GPU configurations and smaller-memory operation
have not been qualified. Install [Miniforge](https://github.com/conda-forge/miniforge)
if Conda is unavailable.

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
```

## Choose a version

**Current source: 0.7.0.** From this checkout:

```sh
python -m pip install ".[VSA]"
```

VSA needs no native engine. SOL requires the matching local engine archive or
the [pinned-source build](development.md#build-the-engine-artifact). Its manifest
URL is unset; source installation cannot download that unpublished archive.
SOL also requires the new model recipe described below.

**Published wheel: 0.6.0.** This older release has no X2 and retains the old SOL recipe:

```sh
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.6.0/h3_apple-0.6.0-py3-none-any.whl"
```

Use that release's [versioned documentation](https://github.com/RhinoQ/h3-apple/tree/v0.6.0/docs).
Repeat the chosen installation command with `--upgrade` to reinstall it.

| Workload | Python | Extra dependencies |
| --- | --- | --- |
| VSA, with or without X2 | 3.11 | `[VSA]` |
| SOL + X2 | 3.11 | `[VSA]`, SOL models and engine; no VSA model bundle needed |
| SOL without X2 | 3.11–3.14 | None; omit `[VSA]` |
| Face enhancement | 3.11 | `[faces]`; see [setup](face-enhancement.md) |

Conda supplies FFmpeg 8, ffprobe and shared libraries; pip installs Python
dependencies. The `[VSA]` extra pins MLX, PyTorch and Transformers. A SOL-only
installation needs neither those packages nor a compiler when its matching
engine is cached. `python -m h3_apple` is equivalent to `h3`.

## Prepare and reuse models

First generation prepares missing models automatically. To inspect costs first:

```sh
h3 prepare --mode VSA --plan
h3 prepare --mode SOL --plan
```

| Mode | Fresh downloads | Conservative additional disk | Prepared footprint |
| --- | ---: | ---: | ---: |
| VSA | ~151 GB | ~343 GB | ~111 GB with hard links; 178 GB logical |
| SOL | ~145 GB | ~233 GB | ~85 GB |

Source caches reduce downloads. Cross-volume copies may use the full logical
size. These are disk estimates, not runtime memory. Actual plans are authoritative.
The CLI asks before downloads above 20 GB. Noninteractive calls require
`--allow-large-download`; Python raises `DownloadApprovalRequired` until
`allow_large_download=True` is supplied. Interrupted downloads resume and are checked.

| Mode | Default directory | Environment override |
| --- | --- | --- |
| VSA | `~/Models/h3-apple/VSA` | `H3_VSA_MODEL_DIR` |
| SOL | `~/Models/h3-apple/ref2va` | `H3_MODEL_DIR` |

`--model-dir` / `model_dir` overrides the selected mode's directory. Keep formats
separate. Reuse compatible bundles or cached raw sources with repeatable
`--reuse-dir` arguments:

```sh
h3 prepare --mode VSA --reuse-dir /path/to/existing-models
h3 doctor --mode VSA
h3 verify --mode VSA
```

VSA accepts the pinned original LightX2V recipe, not DARE/TIES. It imports only
50 FastH3 gates, excluding T2VA adapter deltas. Content identities are fixed in
[model sources](../src/h3_apple/data/model-sources.json) and
[gate sources](../src/h3_apple/data/vsa-gates.json). Model licenses apply.

## Upgrading SOL models in the source checkout

0.7.0 merges Turbo into the original BF16 DiT in FP32, rounds to BF16, then
prepares W8G64 weights. Generation rejects a second Turbo application and old
quantized bundles. Editing a manifest cannot convert the old weights.

Prepare a new directory with the matching engine. Cached original sources can
avoid downloads; an old quantized bundle alone cannot:

```sh
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged \
  --reuse-dir /path/to/original-H3-snapshot --reuse-dir /path/to/adapter.safetensors --plan
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged \
  --reuse-dir /path/to/original-H3-snapshot --reuse-dir /path/to/adapter.safetensors
h3 verify --mode SOL --model-dir ~/Models/h3-apple-sol-premerged
```

Select the new directory on subsequent calls. Preparation preserves existing
models. Four forwards, video/audio shifts 12/3 and adapter scale 1.0 remain fixed.

## Checks and optional components

`h3 doctor --mode VSA` or `--mode SOL` checks hardware, media tools, engine and
model receipts. `h3 verify` performs full model checksums. Generation reserves
20 GiB temporary disk and stops on swap growth above 2 GiB or serious thermal
pressure. Failed jobs retain logs.

[X2](x2.md#model-preparation) adds a separate 5.25 GB decoder.
[Face enhancement](face-enhancement.md) adds a separate 7.08 GB model set and
component terms. Neither is downloaded for ordinary generation.
