# Installation

Two steps: install, then generate. Models are prepared automatically on first use.

## Before you start

- **Mac:** 40-core M5 Max, macOS 26.2+, at least 64 GiB unified memory.
  Measurements used 128 GiB; smaller-memory operation is unverified.
  Other GPU configurations are unsupported. Native 768p beyond five seconds needs 96 GiB.
- **Storage:** fresh VSA setup needs about **151 GB of downloads and
  343 GB of free disk**. Existing caches can reduce this.
- **Conda:** use your existing installation, or install
  [Miniforge for Apple Silicon](https://github.com/conda-forge/miniforge#miniforge3).

## 1. Install

Open Terminal and run:

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
```

This supports **VSA, SOL and X2**. Models download only when needed;
no compiler or manual model download is required.

## 2. Generate your first video

Replace `reference.jpg` with the path to one of your images, and run:

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music." \
  --duration 5 --output first-video.mp4
```

H3 shows download and disk requirements and asks before downloading more than
20 GB. Review the estimate, then enter `y`. Initial setup takes extra time;
later runs reuse the models.

Open **`first-video.mp4`**: a five-second 576p video with stereo audio.
Use a new output filename each time. In a new terminal, run `conda activate h3` first.

**Ready to go further?** [Faster SOL + X2 generation](../README.md#faster-generation) ·
[Portrait and other options](../README.md#generate) · [Python API](api.md).
You can start directly with SOL + X2 after step 1; it does not need VSA models.

## Optional setup

<details>
<summary>Check download and disk costs before generating</summary>

Preview costs without downloading models:

```sh
h3 prepare --plan
h3 prepare --mode SOL --plan
h3 prepare-x2 --plan
```

| Mode | Fresh downloads | Additional free disk for setup | Prepared models |
| --- | ---: | ---: | ---: |
| VSA | ~151 GB | ~343 GB | ~111 GB with hard links; 178 GB logical |
| SOL | ~145 GB | ~233 GB | ~85 GB |

Conservative estimates exclude X2's **5.25 GB** decoder. Caches reduce costs; cross-volume
copies may use the full logical size. Your local plan is authoritative.
SOL's matching 6.05 MB engine downloads automatically.

Unattended downloads above 20 GB need `--allow-large-download` after reviewing the plan;
see [Python consent](api.md) for the API. Interrupted downloads resume on retry.

</details>

<details>
<summary>Reuse models or put them on another drive</summary>

| Mode | Default directory | Environment override |
| --- | --- | --- |
| VSA | `~/Models/h3-apple/VSA` | `H3_VSA_MODEL_DIR` |
| SOL | `~/Models/h3-apple/ref2va` | `H3_MODEL_DIR` |

Set the variable in each session, or pass `--model-dir /path/to/models` each time.
Keep VSA and SOL directories separate. Reuse compatible models or raw sources with:

```sh
h3 prepare --reuse-dir /path/to/existing-models
```

Add `--mode SOL` for SOL; repeat `--reuse-dir` for multiple sources.
Accepted recipes: [model sources](../src/h3_apple/data/model-sources.json),
[VSA gates](../src/h3_apple/data/vsa-gates.json), [implementation](development.md).
Model licenses apply. [X2 uses a separate directory](x2.md#model-preparation).

</details>

<details>
<summary>Upgrade an existing installation</summary>

Activate `h3` and rerun the pip command with `--upgrade`. For an earlier 0.7.0
source/benchmark wheel, use `--force-reinstall` to refresh the engine manifest.
Compatible VSA models are reusable.

### Upgrading SOL models

0.7.0 rejects old quantized SOL weights; editing their manifest cannot upgrade
them. Prepare an empty directory:

```sh
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged --plan
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged
```

To reuse original H3 weights and the Turbo adapter, add
`--reuse-dir /path/to/original-sources` to both commands. Old quantized weights alone are insufficient.
Use `--model-dir ~/Models/h3-apple-sol-premerged` on subsequent SOL calls.
Existing models are preserved. [Why the recipe changed](releases/0.7.0.md#fixes-and-lessons-that-affected-adoption).

</details>

<details>
<summary>Check an installation or troubleshoot a failed run</summary>

`h3 doctor` checks installation readiness; `h3 verify` checks all model-file
checksums. Add `--mode SOL` for SOL. **Missing models before first use are expected**;
generation prepares them.

If `h3` is not found, activate the environment or use `python -m h3_apple`.
Failed jobs retain logs. Generation reserves 20 GiB temporary disk and stops
on swap growth above 2 GiB or serious thermal pressure.

</details>

[Source installation and development](development.md#verify-a-change) ·
[Optional face enhancement](face-enhancement.md)
