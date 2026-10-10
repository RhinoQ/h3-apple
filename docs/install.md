# Installation

## Before you start

- **Mac:** 40-core M5 Max, macOS 26.2+, 64 GiB minimum. Tested with 128 GiB;
  smaller-memory operation is unverified. Other GPUs are unsupported.
- **Disk:** fresh VSA setup needs about **151 GB of downloads / 343 GB free**.
- **Conda:** use your installation or [Miniforge for Apple Silicon](https://github.com/conda-forge/miniforge#miniforge3).

## 1. Install

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
```

One environment supports VSA, SOL and X2. No compiler is needed.

## 2. Generate

SOL + 544p/X2 is the default. Replace `reference.jpg` with your image path:

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music." \
  --duration 5 --output first-video.mp4
```

First use prepares the models. Review the download estimate and enter `y` to
approve transfers over 20 GB. Later runs reuse the models.

Open `first-video.mp4`. Choose a new filename for each run.
In a new terminal, run `conda activate h3` first.

[Output options](x2.md) · [Python API](api.md)

## Optional setup

<details>
<summary>Download and disk costs</summary>

| Mode | Fresh downloads | Free disk for setup |
| --- | ---: | ---: |
| SOL + X2, default | ~150 GB | ~239 GB |
| VSA + X2 | ~156 GB | ~349 GB |

These conservative estimates include X2's 5.25 GB decoder. Caches reduce costs.
SOL's 6.05 MB engine downloads automatically. SOL + X2 does not need VSA models.

Preview your actual costs without downloading:

```sh
h3 prepare --plan
h3 prepare --mode VSA --plan
h3 prepare-x2 --plan
```

Prepared bundles occupy about 111 GB for VSA with hard links (178 GB logical)
or 85 GB for SOL. Cross-volume copies may use the logical size.

Unattended transfers over 20 GB require `--allow-large-download` after plan review.
[Python consent](api.md) is separate. Interrupted downloads resume on retry.

</details>

<details>
<summary>Model locations and reuse</summary>

| Mode | Default directory | Override |
| --- | --- | --- |
| VSA | `~/Models/h3-apple/VSA` | `H3_VSA_MODEL_DIR` |
| SOL | `~/Models/h3-apple/ref2va` | `H3_MODEL_DIR` |

Set the variable in each session or pass `--model-dir`. Keep formats separate.
[X2 has its own directory](x2.md#model-preparation).

```sh
h3 prepare --reuse-dir /path/to/existing-models
```

Add `--mode VSA` for VSA. Repeat `--reuse-dir` for multiple compatible sources.
[Model recipes](development.md) and licenses still apply.

</details>

<a name="upgrading-sol-models"></a>

<details>
<summary>Upgrade h3-apple or older SOL models</summary>

Activate `h3` and rerun the pip command with `--upgrade`.
For an earlier 0.7.0 install, add `--force-reinstall --no-cache-dir`: the refreshed
release changes defaults and removes face enhancement. For native output, specify
`--resolution 576p --no-x2` or `--resolution 768p --no-x2`.
Compatible VSA models are reusable.

**0.7.0 rejects old quantized SOL weights.** Prepare a new directory:

```sh
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged --plan
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged
```

To reuse original H3 weights and Turbo, add `--reuse-dir /path/to/sources` to both
commands. Old quantized weights alone are insufficient. Pass the new `--model-dir`
on later SOL calls. Existing models are preserved.
[Recipe change](releases/0.7.0.md#fixes-and-lessons-that-affected-adoption).

</details>

<details>
<summary>Troubleshooting</summary>

- `h3` not found: activate the environment or use `python -m h3_apple`.
- `h3 doctor` checks readiness; missing models before first use are expected.
- `h3 verify` checks all model checksums. Both default to SOL; use `--mode VSA` for VSA.
- Generation reserves 20 GiB temporary disk and stops on serious thermal pressure
  or swap growth above 2 GiB. Failed jobs retain logs.
- Native 768p over five seconds needs 96 GiB memory.

</details>

[Source installation](development.md#verify-a-change)
