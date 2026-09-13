# H3 Apple

**Generate video with stereo audio locally on Apple M5.**

**28 videos · 14 side-by-side comparisons · native 768p · no cloud inference**

**Tested hardware: M5 Max with 128 GiB unified memory.**
[Hardware requirements and measured memory use](#hardware-and-memory).

Across ten five-second prompts, H3 Apple averaged **5m 56s** from launch to a
validated MP4, versus **9m 07s** for vpipe / VDN: **34.8% less waiting** on the
tested M5 Max. Watch every pair below, with generation times on screen.

[Pre-release v0.1.0.dev1](https://github.com/RhinoQ/h3-apple/releases/tag/v0.1.0.dev1) ·
[Install](#generate-your-first-video) · [Python / CLI API](docs/api.md) ·
[Native video downloads](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11) ·
[Reproduce the comparison](benchmarks/README.md)

The current development build adds [ordered reference images](docs/ref2va.md)
and a [terminal progress bar](docs/api.md#terminal-progress). These features
are newer than the published v0.1.0.dev1 release; use this checkout's installer.

## Video comparisons

**Left: H3 Apple (Ours). Right: vpipe / VDN.**
[Playback, measurement and review notes](#measurement-and-review-scope).

### Fifteen seconds · two additional cinematic scenes

#### Crystal flowers · 15 seconds

**Ours 25m 31s · vpipe 29m 46s · 14.3% less waiting**

https://github.com/user-attachments/assets/7b21948e-c7ff-4e11-98e9-998c577c0afa

[Full prompt](benchmarks/prompts/cinematic-two-15s/lunar-flower-walk.txt) · Seed 15012 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-lunar-flower-walk-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-lunar-flower-walk-vpipe.mp4) · [Run report](benchmarks/results/cinematic-two-15s-01/README.md)

#### The hidden key · 15 seconds

**Ours 24m 52s · vpipe 29m 27s · 15.5% less waiting**

https://github.com/user-attachments/assets/ce84e0f7-0bdb-430b-8a7c-243699fa0818

[Full prompt](benchmarks/prompts/cinematic-two-15s/archive-discovery.txt) · Seed 15011 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-archive-discovery-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-archive-discovery-vpipe.mp4) · [Run report](benchmarks/results/cinematic-two-15s-01/README.md)

### Five seconds · all ten prompts

#### Motion graphics · 5 seconds

**Ours 5m 54s · vpipe 8m 49s · 33.0% less waiting**

https://github.com/user-attachments/assets/0e3eae3a-77ef-4d11-a9d4-352b131d16aa

[Full prompt](benchmarks/prompts/motion-graphics-5s.txt) · Seed 2026 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-motion-graphics-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-motion-graphics-vpipe.mp4) · [Run report](benchmarks/results/short-768p-01/README.md)

#### Bakery at dawn · 5 seconds

**Ours 5m 55s · vpipe 9m 01s · 34.3% less waiting**

https://github.com/user-attachments/assets/8da8c165-ece5-4a1d-b46e-f88246047cd9

[Full prompt](benchmarks/prompts/bakery-5s.txt) · Seed 87001 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-bakery-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-bakery-vpipe.mp4) · [Run report](benchmarks/results/short-768p-01/README.md)

#### The old sailor · 5 seconds

**Ours 5m 56s · vpipe 8m 57s · 33.8% less waiting**

https://github.com/user-attachments/assets/aefc485f-a1ab-46c1-8fd5-4dc4593c441a

[Full prompt](benchmarks/prompts/short-diverse-10/sailor-dialogue.txt) · Seed 11003 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-sailor-dialogue-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-sailor-dialogue-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Rainy night bus · 5 seconds

**Ours 6m 02s · vpipe 9m 08s · 33.9% less waiting**

https://github.com/user-attachments/assets/52d84846-5b76-48e9-8a89-c11e833ddabf

[Full prompt](benchmarks/prompts/short-diverse-10/night-bus.txt) · Seed 11004 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-night-bus-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-night-bus-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Candy keyboard · 5 seconds

**Ours 5m 41s · vpipe 9m 11s · 38.1% less waiting**

https://github.com/user-attachments/assets/b7a441cf-5f09-49c3-b455-f53a26639e4b

[Full prompt](benchmarks/prompts/short-diverse-10/candy-keyboard.txt) · Seed 11005 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-candy-keyboard-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-candy-keyboard-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Canyon reveal · 5 seconds

**Ours 6m 06s · vpipe 9m 10s · 33.4% less waiting**

https://github.com/user-attachments/assets/ab3478a2-a8a5-4e1d-a9b5-e39dd76c7ca5

[Full prompt](benchmarks/prompts/short-diverse-10/canyon-reveal.txt) · Seed 11006 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-canyon-reveal-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-canyon-reveal-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### A raindrop on a rose · 5 seconds

**Ours 6m 06s · vpipe 9m 13s · 33.8% less waiting**

https://github.com/user-attachments/assets/9bcd6c46-add9-4f10-8c75-4457af4e7a5c

[Full prompt](benchmarks/prompts/short-diverse-10/rose-raindrop.txt) · Seed 11007 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-rose-raindrop-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-rose-raindrop-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Clay campfire and fox · 5 seconds

**Ours 5m 49s · vpipe 9m 10s · 36.6% less waiting**

https://github.com/user-attachments/assets/c1931f46-3cd4-4e4a-b122-e0530d439b7e

[Full prompt](benchmarks/prompts/short-diverse-10/clay-campfire-fox.txt) · Seed 11008 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-clay-campfire-fox-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-clay-campfire-fox-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Field mouse · 5 seconds

**Ours 6m 07s · vpipe 9m 12s · 33.6% less waiting**

https://github.com/user-attachments/assets/62c2e37e-9249-4da4-9afd-28274dce14b4

[Full prompt](benchmarks/prompts/short-diverse-10/field-mouse.txt) · Seed 11009 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-field-mouse-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-field-mouse-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

#### Opening an umbrella · 5 seconds

**Ours 5m 47s · vpipe 9m 14s · 37.4% less waiting**

https://github.com/user-attachments/assets/430e5d53-9e9d-43a3-a4dc-e52a0bafaa6f

[Full prompt](benchmarks/prompts/short-diverse-10/umbrella-opening.txt) · Seed 11010 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-umbrella-opening-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/5s-umbrella-opening-vpipe.mp4) · [Run report](benchmarks/results/short-diverse-10-01/README.md)

### Fifteen seconds · original motion graphics and bakery

#### Motion graphics · 15 seconds

**Ours 36m 47s · vpipe 41m 15s · 10.8% less waiting**

https://github.com/user-attachments/assets/7e2fefe7-cb23-4ac4-82f1-4af2984e8db5

[Full prompt](benchmarks/prompts/motion-graphics.txt) · Seed 2026 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-motion-graphics-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-motion-graphics-vpipe.mp4) · [Run report](benchmarks/results/native-three-02/README.md)

#### Bakery at dawn · 15 seconds

**Ours 33m 18s · vpipe 39m 30s · 15.7% less waiting**

https://github.com/user-attachments/assets/bf551d69-99e0-49e1-90d1-87385a19799a

[Full prompt](benchmarks/prompts/bakery.txt) · Seed 87001 · [Ours — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-bakery-ours.mp4) · [vpipe — native 768p](https://github.com/RhinoQ/h3-apple/releases/download/benchmark-videos-2026-09-11/15s-bakery-vpipe.mp4) · [Run report](benchmarks/results/native-three-02/README.md)

### Measurement and review scope

**Left: H3 Apple (Ours). Right: vpipe / VDN.**
All videos play at their original speed and full duration. Preview panels are
640×360; timings refer to the original **1366×768, 24 fps** deliveries.
**Preview audio is Ours**; each native download has its own 32 kHz stereo audio.

Measured on **Apple M5 Max / 128 GiB / macOS 26.6.1**. Times include fresh-process
loading, compilation, generation, full decoding, muxing, and final media checks.
Each input/system ran once with a fixed recipe. The original eight videos have
[human acceptance](benchmarks/reviews/existing-eight-20260911.json); the twenty
additional videos await human quality review, with
[observed issues retained](benchmarks/results/short-diverse-10-01/README.md#videos-and-quality).

| Test set | Ours mean wait | vpipe / VDN mean wait | Wait reduction |
| --- | ---: | ---: | ---: |
| 5 seconds · all 10 prompts | 5m 56s | 9m 07s | 34.8% |
| 15 seconds · 2 cinematic prompts | 25m 12s | 29m 36s | 14.9% |
| 15 seconds · motion graphics + bakery | 35m 02s | 40m 23s | 13.2% |

These are observed system timings, not a repeat-measured speed guarantee or
proof of overall quality superiority. The fifteen-second sets use different
scenes with the same runtime; their difference is not a new code speedup.
These gallery runs predate the GPU residency-policy change. Timings under the
current memory policy are recorded separately in the
[resource tests](benchmarks/results/memory-storage-01/README.md).

The [gallery manifest](examples/gallery/manifest.json) records exact seconds,
video hashes, source snapshots, and preview conversion. All completed Ours/vpipe
outputs from these four rounds are included, without reruns or output selection.
Official FastH3 is outside the current comparison; its
[historical unsuccessful attempts](benchmarks/results/fastvideo-frame-limit-01/README.md)
remain available for inspection.

## Hardware and memory

**M5 Max / 128 GiB is the physically tested configuration.** This preview
requires an M5 GPU and macOS 26.2 or later. **64 GiB support is experimental:**
smaller workloads passed total-budget tests on our 128 GiB host, but physical
64 GB M5 Pro and M5 Max machines still need validation. This does not mean
every M5 Mac can run H3. Machines below 64 GiB are rejected before loading models.

| Workload | Entry memory minimum | Complete budget test | H3 process-tree peak |
| --- | ---: | --- | ---: |
| 768p / 5 seconds | 64 GiB | Two prompts passed at 64 GiB | 34.41–35.13 GiB |
| 576p / 5–15 seconds | 64 GiB | One 15-second prompt passed at 64 GiB | 40.95 GiB |
| Model preparation | 64 GiB | Full reconstruction passed at 64 GiB; all 35 model files matched | 31.18 GiB |
| 768p / longer than 5 seconds, up to 15 seconds | 96 GiB | One 15-second prompt passed at 96 GiB | 56.27 GiB |

A **768p / 15-second attempt failed at 64 GiB**, exceeding the test's swap-growth
limit; it produced no completed video. On a 64 GiB Mac, start with `--duration 5`
or use `--resolution 576p` for a 15-second video. The entry returns these smaller
alternatives when a long 768p request exceeds its admitted memory range.

The 64 GiB tests locked half of the 128 GiB Mac's physical pages, leaving
64 GiB for macOS, other applications and H3 together. All completed tests had
normal memory pressure and **zero swap growth**. The two short MP4s and the 96 GiB long MP4 exactly
matched their gallery originals. Process-tree peaks are sampled macOS physical
footprints, not a Mac's minimum RAM requirement; GPU-only MLX peaks also omit
other allocations. **64 GiB is the lowest tested total budget, not an established
absolute minimum or physical 64 GB certification.** The GPU and its device
limits remain those of the actual host. See the
[resource report and exact measurements](benchmarks/results/memory-storage-01/README.md).

Apple's [base M5 MacBook Pro](https://support.apple.com/en-us/125405) tops out at
32 GB. The [M5 Pro/Max configurations](https://support.apple.com/en-us/126318)
meeting the 64 GB floor are M5 Pro with a 20-core GPU and M5 Max with a 40-core
GPU. Other M-series generations are not supported by this build. Run one H3 job
at a time, use AC power, and close other memory-heavy apps; disk swap is not a
substitute for enough unified memory.

### Disk space

**Start with at least 200 GiB free (about 215 GB)** for the default installation,
with the source cache and prepared models on the same APFS volume. This is a
rounded recommendation based on measured preparation usage plus the environment
and generation headroom; it is not an exact minimum disk capacity.

| Storage item | Measured size or requirement |
| --- | ---: |
| Pinned source downloads, starting from an empty cache | 139.11 GiB of model files; reused locally in this test |
| Source cache + model preparation peak, counting shared hard links once | 170.12 GiB |
| Prepared generation bundle alone | 93.71 GiB |
| Conda environment + private Conda package cache | About 1.7 GiB allocated |
| Free space required when generating, in addition to retained files | **20 GiB**; checked by the worker |

After successful preparation and verification, the original source cache is
optional for everyday offline generation. Keeping the prepared bundle and
environment, with 20 GiB left free, fits within a **120 GiB total disk budget
(about 129 GB)** before accumulated videos. Keeping the source cache makes
future rebuilding easier. Shared files must be counted once; the source cache
and bundle sizes must not be added together.

The preparation test rebuilt all converted files, verified their content and
measured peak storage; it reused the complete source cache rather than
redownloading 139 GiB. Different cache/model volumes require extra copies.
Run `h3 models prepare --plan` for the actual additional space on each volume,
and see [model storage and reuse](docs/models.md). Diagnostic tensor exports
are outside these everyday-generation figures.

## Generate your first video

This is a community project built on MiniMax-H3, FastVideo, and Apple GPU
optimizations, with no official affiliation. The latest published package is
**[0.1.0.dev1 (development preview)](https://github.com/RhinoQ/h3-apple/releases/tag/v0.1.0.dev1)**.
The release includes a source archive, Python wheel, and SHA-256 checksums.
Check the [hardware and memory requirements](#hardware-and-memory)
before installing.

Install ARM64 [Miniforge](https://github.com/conda-forge/miniforge) or use your
existing Conda installation:

```bash
git clone --branch v0.1.0.dev1 --single-branch https://github.com/RhinoQ/h3-apple.git
cd h3-apple
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 models prepare --plan
```

Read the [MiniMax-H3 model terms](licenses/MiniMax-H3.txt) and review the download
plan before preparing weights. Check the [disk-space budget](#disk-space)
and [storage and reuse](docs/models.md) before starting. Downloads above
20 GB require the explicit flag below:

```bash
h3 models prepare --allow-large-download
h3 doctor
h3 generate --prompt "A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell." --seed 87001 --duration 5 --output bakery.mp4
```

Reuse existing files with `--reuse-dir`. Once prepared, generation runs offline.
Without duration/resolution flags, the API defaults to **768p / 15 seconds /
24 fps with stereo audio**, which requires at least 96 GiB. The command above
uses five seconds so it also fits the experimental 64 GiB entry. For a smaller
first run, add `--resolution 576p`.

Each run returns an MP4 and adjacent `.run.json` with the actual dimensions,
seed, time, version, and model identity. Existing files are never overwritten.
Ctrl-C cancels the worker and preserves failure logs.

```python
from h3_apple import generate

result = generate(
    "A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell.",
    resolution="768p",
    duration=5,
    seed=87001,
    output="bakery-short.mp4",
)
print(result.video_path)
print(result.elapsed_seconds)
```

[Installation and recovery](docs/install.md) · [Models](docs/models.md) ·
[All API parameters](docs/api.md) · [Runnable Python example](examples/generate.py)

## What you get

| Capability | H3 Apple |
| --- | --- |
| Everyday interface | One CLI and Python API for text or ordered reference images |
| Video and audio | 768p or 576p, 5–15 seconds, 24 fps, stereo audio |
| Generation recipe | Four-step VSA, M5 NAX sparse kernels, accelerated full H3 VAE |
| Reproducibility | Locked Conda environment, verified model preparation, recorded seeds and asset identity |
| Process control | Separate worker, progress, cancellation, timeout, shared device lock |
| Optional comparison | Fixed Ours/vpipe VDN suites with complete delivery timing |

Independent installation, model reconstruction, real generation, numerical
migration, and GPU cancellation have passed the checks recorded in
[validation](docs/validation.md). The current development interface supports
text or 1–9 ordered still images with audio output. Reference generation needs
a [dedicated model bundle](docs/ref2va.md); its tested cases are one and four
images at 576p on M5 Max / 128 GiB. Training, video/audio reference input,
a web service and videos longer than fifteen seconds are not exposed.

## Reproduce and improve

Ordinary generation needs only this repository. To compare against the pinned
vpipe VDN recipe, follow [benchmark preparation](benchmarks/README.md), then run:

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json
```

The systems have different weights, adapters, precision, and sampling recipes.
Their total wait difference is a product comparison, not an isolated operator
ablation. Untested methods are not ranked.

For implementation details and contributing changes, see
[architecture](docs/architecture.md) and [development](docs/development.md).

## Acknowledgments

Thanks to [MiniMax](https://huggingface.co/MiniMaxAI/MiniMax-H3) for H3,
[FastVideo / FastH3](https://github.com/hao-ai-lab/FastVideo) for the MLX runtime
and VSA adapter, and [MLX](https://github.com/ml-explore/mlx) for Apple silicon
support. Our Metal kernels build on
[mlx-flashattention-steel (MFA)](https://github.com/marcogva-hub/mlx-flashattention-steel),
[Draw Things / CCV](https://github.com/liuliu/ccv), and
[h3.c](https://github.com/antirez/h3.c). We also thank
[vpipe](https://github.com/tgo-app-dev/vpipe) for the comparison baseline,
and all upstream authors and contributors for sharing their work.

Our code is Apache-2.0. Upstream code, model weights, and calibration material
retain their own terms; see [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).
Weights and large logs are excluded from Git.
