# H3 Apple

**Generate video with stereo audio locally on Apple M5.**

**28 videos · 14 side-by-side comparisons · native 768p · no cloud inference**

**Tested hardware: M5 Max with 128 GiB unified memory.**
[Hardware requirements and measured memory use](#hardware-and-memory).

Across ten five-second prompts, H3 Apple averaged **5m 56s** from launch to a
validated MP4, versus **9m 07s** for vpipe / VDN: **34.8% less waiting** on the
tested M5 Max. Watch every pair below, with generation times on screen.

[Release v0.2.0](https://github.com/RhinoQ/h3-apple/releases/tag/v0.2.0) ·
[Install](#generate-your-first-video) · [Python / CLI API](docs/api.md) ·
[User guide: modes, references, quality and waiting time](docs/user-guide.md) ·
[Native video downloads](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11) ·
[Reproduce the comparison](benchmarks/README.md)

**0.2.0** supports text (**T2VA**), first/last frames (**FL2VA**, LightX2V v1.2),
and pictures or videos (**Ref2VA**), with optional audio references.
**First time? [Start with a five-second text video](#generate-your-first-video).**
The automatic model downloader prepares T2VA; FL2VA and Ref2VA need separate
bundles and additional setup. [Choose a mode](#use-your-own-images-video-or-audio).

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

**M5 Max / 128 GiB is the physically tested configuration.** This release
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

These are **text-generation budget tests on a 128 GiB host**, not tests of
physical 64 GB machines or FL2VA/Ref2VA memory requirements. Process-tree peaks
are measured footprints, not minimum RAM specifications. A **768p / 15-second
attempt failed at 64 GiB** due to swap growth. On a 64 GiB Mac, use
`--duration 5` or `--resolution 576p` for longer clips.

Run one H3 job at a time and close other memory-heavy apps. Reference encoders
and additional reference frames add work and memory. The [resource report](benchmarks/results/memory-storage-01/README.md)
contains the complete budget method, successful runs and failure evidence.

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

After verified preparation, the source cache is optional for offline generation;
keeping it makes future rebuilding easier. The prepared text bundle, environment
and 20 GiB free headroom fit within a **120 GiB total budget**, before accumulated
videos. Shared hard links count once; separate volumes need extra copies.

The preparation measurement reused verified source files. Run
`h3 models prepare --plan` for your actual download and disk requirements.
FL2VA/Ref2VA source preparation and diagnostic tensor exports are outside this
text-model budget. See [model storage and reuse](docs/models.md).

## Generate your first video

You need an **M5 Mac, macOS 26.2+, at least 64 GiB unified memory**, and
**200 GiB free disk** for the first text-model setup. Physical testing covers
M5 Max / 128 GiB; see [hardware limits](#hardware-and-memory) before using a
smaller machine. Run on AC power. H3 Apple is a community project with no
official MiniMax or Apple affiliation.

**1. Install.** Install ARM64 [Miniforge](https://github.com/conda-forge/miniforge)
or use an existing ARM64 Conda installation. Download and unzip the
[v0.2.0 source archive](https://github.com/RhinoQ/h3-apple/releases/download/v0.2.0/h3-apple-0.2.0-source.zip).
Open Terminal and enter its extracted folder:

```bash
cd ~/Downloads/h3-apple-0.2.0
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 --version
```

Change the `cd` path if you extracted elsewhere. The source archive includes
the installer; the wheel alone does not. [Git installation, checksums and
recovery](docs/install.md) are available separately.

**2. Prepare the text model once.** Inspect the plan first:

```bash
h3 models prepare --plan
```

A fresh setup downloads about **139 GiB**, then converts the weights locally.
Read the [model terms](licenses/MiniMax-H3.txt) and [storage/reuse guide](docs/models.md).
If the plan fits your disk and download budget, explicitly allow the download:

```bash
h3 models prepare --allow-large-download
h3 doctor
```

Wait for preparation to finish and `doctor` to report `"ready": true`.
Models default to `~/Models/h3-apple`. To use an existing **prepared bundle**,
pass `--model-dir /path/to/bundle` to `doctor` and `generate`, or set
`H3_MODEL_DIR`. `--reuse-dir` is for reusing **source downloads** during preparation.
Once prepared, generation runs offline.

**3. Generate and play.** This command creates five seconds of video and stereo sound:

```bash
h3 generate --prompt "A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell." --resolution 768p --duration 5 --seed 87001 --timeout 1800 --output bakery.mp4
open bakery.mp4
```

Wait for **Complete**: denoising is followed by video/audio decoding and validation.
The result is `bakery.mp4` plus `bakery.run.json`, recording the prompt, seed,
dimensions, timing, software and model identity. Use a new output filename
for another run; existing results are never overwritten. Ctrl-C cancels the
worker. The 30-minute timeout stops an unfinished run; failed/cancelled runs
retain their record and worker logs.

Keep `--duration 5` for initial checks: omitting it requests **15 seconds**,
and 768p above five seconds requires at least 96 GiB. `--resolution 576p`
reduces work; prefer 768p for small faces and fine details. The gallery's
five-second text runs averaged about six minutes on the tested M5 Max;
that is not an ETA for other modes or inputs.

[Python example](examples/generate.py) · [All API parameters](docs/api.md) ·
[Installation and recovery](docs/install.md) · [Validation scope](docs/validation.md)

## Use your own images, video or audio

Choose a mode by what the reference should do:

| Input / purpose | Mode | Model setup | Attention |
| --- | --- | --- | --- |
| Text description | T2VA | Automatic `h3 models prepare` | VSA |
| Starting image, ending image, or both | FL2VA | [Separate LightX2V v1.2 conversion and bundle](docs/fl2va.md#prepare-and-generate) | VSA |
| Pictures for identity, objects, setting or style | Ref2VA | [Separate Ref2VA conversion and bundle](docs/ref2va.md#installation-and-models) | VSA |
| Reference video and/or audio, with a picture or video | Ref2VA | Same Ref2VA bundle; [video](docs/ref2va-video.md) / [audio](docs/ref2va-audio.md) guide | Dense |

**FL2VA and Ref2VA setup is currently manual.** `--task` does not download or
switch model weights automatically. Both require the optional vision packages:
run `./install.sh --ref2va` from the extracted source folder, then follow the
linked conversion guide. The extra's name also applies to FL2VA.

After preparing the matching bundle, replace the image paths below with your
own files. First/last anchors guide the endpoints; ordered reference pictures
guide the content throughout the clip.

```bash
h3 doctor --model-dir ~/Models/h3-apple-fl2va-v12
h3 generate --task fl2va --prompt "A smooth continuous shot from Picture 1 to Picture 2, with natural ambience." --first-frame first.png --last-frame last.png --model-dir ~/Models/h3-apple-fl2va-v12 --resolution 768p --duration 5 --seed 42 --timeout 1800 --output keyframes.mp4

h3 doctor --model-dir ~/Models/h3-apple-ref2va
h3 generate --task ref2va --prompt "Use Picture 1 for the subject and setting. A slow camera move with natural ambience." --reference-image reference.jpg --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 5 --seed 42 --timeout 1800 --output reference.mp4
```

FL2VA also accepts just one anchor. Ref2VA supports up to nine ordered images;
name their roles as Picture 1, Picture 2, etc. Image-only Ref2VA otherwise
defaults to **576p**. Clear original references matter: `--reference-resize match`
can retain more detail from large images, with extra cost; it cannot restore
detail absent from the source. [Image-size policy](docs/ref2va.md#image-size-policy).

Video and independent audio references select **Dense** and can take much
longer, including over an hour for larger requests. Use `--timeout 3600` if
one hour is your limit. Audio requires a picture or video and guides newly
generated sound. Precise preservation of faces, scene, motion, voice or text
is not guaranteed. [Practical limits and measured waiting times](docs/user-guide.md).

All modes default to landscape. `--aspect-ratio 9:16` enables experimental
[portrait output](docs/api.md#portrait-output); consult its validation limits.

## What you get

| Capability | H3 Apple |
| --- | --- |
| Everyday interface | One CLI and Python API for text, first/last frames, or ordered reference images/videos with optional audio |
| Video and audio | 768p or 576p, 5–15 seconds, 24 fps, stereo audio |
| Generation recipe | Four steps; VSA with M5 NAX kernels for text, keyframes and image-only references; Dense for video/audio references; accelerated full H3 VAE |
| Reproducibility | Locked Conda environment, verified model preparation, recorded seeds and asset identity |
| Process control | Separate worker, progress, cancellation, timeout, shared device lock |
| Optional comparison | Fixed Ours/vpipe VDN suites with complete delivery timing |

Independent installation, model reconstruction, real generation, numerical
migration, and GPU cancellation have passed the checks recorded in
[validation](docs/validation.md). The public interface supports
text, first/last keyframes, or 1–9 ordered images and/or 1–3 videos with audio output. FL2VA
needs its [v1.2 bundle](docs/fl2va.md). Reference generation needs
a [dedicated model bundle](docs/ref2va.md). Its limited validation covers
one and four images at 576p and a five-second video-reference regression at
768p on M5 Max / 128 GiB. [Video editing can still change the source scene or motion](docs/ref2va-video.md).
Independent audio can accompany Ref2VA images or videos; a [six-second 768p execution check](benchmarks/results/ref2va-audio-01/README.md) includes full reproduction details and separate voice/synchronization limits. Training, a web service and output videos
longer than fifteen seconds are not exposed.

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
