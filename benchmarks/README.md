# Compare completed videos

Choose a suite by the duration you want to deliver:

| Delivery | Suite | Current comparison |
| --- | --- | --- |
| 768p / 5 seconds | `suites/motion-bakery-5s.json` | Ours, vpipe / VDN |
| 768p / 5 seconds, ten prompts | `suites/diverse-10-5s.json` | Ours, vpipe / VDN |
| 768p / 15 seconds | `suites/motion-bakery.json` | Ours, vpipe / VDN |
| 768p / 15 seconds, two additional cinematic scenes | `suites/cinematic-two-15s.json` | Ours, vpipe / VDN |

[Watch all 14 completed pairs](../README.md#video-comparisons) ·
[Download the 28 native videos](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11)

Short prompts were adapted in advance to five-second actions, rather than
truncating fifteen-second narratives. The original suites use motion graphics
with seed 2026 and bakery with seed 87001. Each suite records full text and
SHA256. These public inputs and adaptations are not held-out or blind-test data.

`compare.py` calls the Ours/vpipe CLIs directly. Generation users need only Ours.
The benchmark does not install, upgrade, or download external projects. Routine
research compares an Ours candidate with the stable version; run vpipe when
updating the external reference.

## Completed evidence

- [native-three-02](results/native-three-02/README.md): six attempts, four complete fifteen-second videos, and two official entry-specification rejections.
- [short-768p-01](results/short-768p-01/README.md): four complete five-second videos; official FastH3 comparison and downloads canceled.
- [short-diverse-10-01](results/short-diverse-10-01/README.md): sixteen new successful five-second videos; together with the retained two pairs, ten prompts and twenty videos.
- [cinematic-two-15s-01](results/cinematic-two-15s-01/README.md): four successful videos from two additional fifteen-second prompts, with fixed inputs and recipes.

The original eight videos received [human audiovisual acceptance](reviews/existing-eight-20260911.json).
The twenty additional videos still await human quality review. Reports preserve
prompt sources, plans, timings, and observed visual issues.

The [two official follow-up attempts](results/fastvideo-frame-limit-01/README.md)
produced raw videos after the entry fix but failed delivery-duration validation
and had damaged late frames. They have no successful delivery timing.

## Run a comparison

1. [Install Ours](../docs/install.md), then prepare or reuse models with `h3 models prepare`.
2. Prepare the required external project below, recording its commit, model sources, and conversion.
3. Copy `local.example.json` to ignored `local.json`. Supply absolute interpreter/binary/model paths, fixed commits, and manifest SHA256 values.

From the product repository:

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py

# Two five-second prompts, four generations.
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/motion-bakery-5s.json --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/motion-bakery-5s.json

# All ten five-second prompts, twenty generations.
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json

# Two additional fifteen-second prompts, four generations.
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json
```

Each entry runs in an independent process in suite order. Official FastH3 is
not required. Ours' `{resolution}` and `{duration}` placeholders come from the
suite, so switching suites does not retain an old duration. Every round creates
a unique directory under `.local/comparisons/` by default. It contains
`results.json`, CSV, a Markdown table, commands, configuration, logs, media,
and resource observations. Failed times are excluded from successful speed
tables. Use `--output /absolute/new/directory` for another unique destination.

`--methods ours` or `--methods vpipe` isolates an entry for diagnosis; describe
partial runs by their actual coverage. Ctrl-C cancels the round and current
process group while preserving cancellation status.

## Pinned external source

Version checked on 2026-09-09:

| Entry | Commit | One-time preparation |
| --- | --- | --- |
| vpipe | `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` | [Official build guide](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/README.md#build-from-source), [H3 model preparation](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/docs/MINIMAX-H3.md) |

The local independent build and delivery adapter completed native 768p
generation for ten five-second and four fifteen-second scenes. The reports
above own actual results and limitations.

Official FastH3 code, original configurations, and the [duration patch](patches/README.md)
remain as historical evidence. It is absent from current suites and the example
configuration. Use the corresponding frozen configuration for reproduction;
old failures remain failures.

vpipe uses the official `docs/pipelines/minimax-h3-vdn.vpipeline` template.
The controller substitutes only text, seed, suite model dimensions/frame count,
output paths, and local model keys. Steps, VDN branch, Turbo adapter, shift,
and quantization remain as configured. Six configured steps do not establish
actual NFE. VDN was selected in advance and does not represent the fastest
possible vpipe recipe.

A local build can use `VPIPE_METAL_RUNTIME_COMPILE=ON` to avoid downloading
another Metal toolchain. Submodules are pinned at the source commit. A separate
Conda environment supplies CMake, Ninja, and FFmpeg headers. The CMake target
is `vpipe-cli` and the executable is `build/apps/vpipe/vpipe`.
`VPIPE_FFMPEG_DIR` points to the Conda `lib` directory matching the header ABI.
vpipe reads `session.json` and its registry from the launch directory, so
`cwd` must be the prepared working directory.

With Apple Command Line Tools installed:

```bash
git clone https://github.com/tgo-app-dev/vpipe.git /path/to/vpipe
git -C /path/to/vpipe checkout 0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d
git -C /path/to/vpipe submodule update --init --recursive
conda create --yes --copy --prefix /path/to/vpipe-build-env -c conda-forge cmake ninja ffmpeg=8.1.2
/path/to/vpipe-build-env/bin/cmake -S /path/to/vpipe -B /path/to/vpipe-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM=/path/to/vpipe-build-env/bin/ninja -DCMAKE_PREFIX_PATH=/path/to/vpipe-build-env -DVPIPE_BUILD_PYTHON=OFF -DVPIPE_BUILD_MACOS_APP=OFF -DVPIPE_METAL_RUNTIME_COMPILE=ON
/path/to/vpipe-build-env/bin/cmake --build /path/to/vpipe-build --target vpipe-cli
```

Follow official preparation in a new working directory. Existing models can be
registered through the native stage to avoid duplicate downloads:

```bash
VPIPE_FFMPEG_DIR=/path/to/vpipe-build-env/lib /path/to/vpipe-build/apps/vpipe/vpipe --launch-stage model-register --stage-cfg model_dir=/path/to/complete-q8-model --stage-cfg key=local/MiniMax-H3-FL2VA-8bit
```

Also register VDN as `OpenVDN/vdn-minimax-h3-stage-dmd` and the Turbo adapter as
`larryvrh/MiniMax-H3-Turbo-Lora-v4-600-ema`, matching the pinned template.
Reuse verified model files only; do not copy or hard-link a writable LMDB
from an old working directory.

## Assets and traceability

Model preparation is outside generation timing; reuse verified existing assets.
Each `asset_receipts` item refers to a JSON manifest whose files received full
SHA256 checks during preparation. Outside the timer, the controller verifies
the manifest's SHA256 and each file's size and modification time. Ours can use
`bundle.json` directly. External receipts use this format, with paths relative
to the receipt or its configured `root`:

```json
{"files": [{"path": "models/example.safetensors", "size": 123, "mtime_ns": 1234567890000000000, "sha256": "actual-full-file-sha256"}]}
```

Record the original base, adapter, quantization/converter, and environment.
A native MiniMax base locally merged with an official adapter is not equivalent
by assertion to a full student snapshot. Different upstream baselines and
recipes make the timing difference a system comparison, not an isolated Ours gain.

`runtime_files` additionally binds installed Python files, MLX libraries/metallibs,
and vpipe dylibs through `{path, sha256}`. Formal configurations check installed
files and source commits together. A source checkout or small CLI executable
alone does not identify the runtime actually loaded.

## Common timing and limits

Delivery is 1366×768, 24 fps, 32 kHz stereo. Five-second delivery has 120 frames
from 1376×768 / 124 model frames; fifteen-second delivery has 360 frames from
1376×768 / 362 model frames. External entries retain their raw MP4, then apply
only center-cropping and tail trimming. No upscaling, interpolation, or temporal
downsampling is used. Ours performs delivery within its API. External adaptation
time is included in user waiting time, with exact commands recorded.
Five- and fifteen-second results are reported separately.

Raw AAC endpoints may differ from native video by at most one packet in either
direction, but audio must cover the entire requested delivery. Short coverage
or a larger mismatch fails without inserted silence. Final outputs still require
strict AV durations and zero start times. Fixes never retroactively pass old failures.

Timing starts before a fresh process and ends after full AV decoding and checks
of dimensions, frames, frame rate, channels, and duration. It includes loading,
compilation, empty-prompt cache work, generation, and muxing. Normal OS and Metal
caches remain. Preparation and waiting for AC/nominal thermal conditions are
recorded separately. Runs start on AC with Low Power Mode off and nominal
thermal state. Serious/critical temperature, more than 2 GiB of swap growth,
less than 20 GiB free disk, or timeout stops the run and preserves evidence.

The Ours worker holds the device lock; the controller holds it for vpipe.
Cooperating H3 jobs must share the lock. A file lock alone cannot discover
unrelated GPU jobs that ignore it.

The controller passes the evaluation environment's FFmpeg PATH to child commands
and records binary identity. An absolute Python path alone does not activate
Conda's executable search path. Cancellation first sends Ctrl-C so Ours can
close its independent GPU worker, then escalates if necessary.

Human quality review starts as `pending`. Media validity does not establish
quality. After viewing complete audio and video, record review conclusions
separately and link immutable result/video hashes. Single runs describe
observations; they do not establish stable speedups, quality superiority,
or generalization.
