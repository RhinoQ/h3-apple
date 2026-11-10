# Installation

## Before you start

- **Mac:** 40-core M5 Max, macOS 26.2+, 64 GiB minimum. Tested with 128 GiB;
  smaller-memory operation is unverified. Other GPUs are unsupported.
- **Disk:** fresh VSA + X2 setup needs about **156 GB of downloads / 351 GB free**.
  SOL + X2 needs about **150 GB / 241 GB**. Existing caches reduce these costs.
- **Conda:** use your installation or [Miniforge for Apple Silicon](https://github.com/conda-forge/miniforge#miniforge3).

## 1. Install

Install the 0.9.0 release wheel in a Python 3.11 Conda environment.

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install https://github.com/RhinoQ/h3-apple/releases/download/v0.9.0/h3_apple-0.9.0-py3-none-any.whl
```

One environment supports generation and super-resolution. No compiler is needed.

## 2. Generate

Save the sample as `rabbit.png`, or substitute your own image path. [Download the rabbit reference](https://raw.githubusercontent.com/RhinoQ/h3-apple/885a874c76664d0781337950d9ddc6ece0ee548e/features/fan-wardrobe/refs/01-rest-3d.png)

```sh
h3 generate --image rabbit.png --output rabbit.mp4 \
  --prompt "The pink rabbit in Picture 1 raises one paw and waves. Its coat rustles."
```

First use prepares the models. Review the download estimate and enter `y` to
approve transfers over 20 GB. Later runs reuse the models.

This writes a five-second video to `rabbit.mp4`. Omitting `--output` creates
a fresh directory under `runs/`. Fast and Medium accept 5–15 seconds aligned
to 24 fps, such as `--duration 7` or `--duration 8.5`. High generates five seconds.
In a new terminal, run `conda activate h3` first.

## 3. Optional super-resolution

Add detail to the saved video, including default X2 output:

```sh
h3 upscale --input rabbit.mp4 --output rabbit-2x.mp4
```

This doubles its dimensions and preserves audio. Requires **128 GiB memory**
and **6.97 GB** of additional models. Restoration takes tens of minutes per
five-second clip, depending on input size, beyond generation time.
[Details and noncommercial terms](upscale.md).

[Advanced settings](advanced.md) · [Python API](api.md)

## Optional setup

<details>
<summary>Download and disk costs</summary>

| Mode | Fresh downloads | Free disk for setup |
| --- | ---: | ---: |
| VSA + X2, default | ~156 GB | ~351 GB |
| SOL + X2 | ~150 GB | ~241 GB |

These conservative estimates include X2's 5.25 GB decoder. Caches reduce costs.
SOL's 6.05 MB engine downloads automatically. SOL + X2 does not need VSA models.
Fast and Medium share the selected backend's generation bundle and default to
VSA. Fast also uses the X2 decoder. High prepares a separate Pika H3 Flex
bundle on first use and delivers native 768p. With the original VSA source
files cached, High adds a 2.77 GB adapter download. Even with all sources on
the same volume, fresh conversion checks for about 192 GB of free disk.
Requesting VOSR 2× adds a separate 6.97 GB model. Combined downloads are
checked before setup.

These commands report setup costs for the selected generator, X2 and VOSR.

```sh
h3 prepare --plan
h3 prepare --mode SOL --plan
h3 prepare --quality high --plan
h3 prepare-x2 --plan
h3 prepare-vosr --plan
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
| VSA, LightX2V v1.0 | `~/Models/h3-apple/VSA-lightx2v-v1` | `H3_VSA_MODEL_DIR` |
| SOL, LightX2V v1.0 | `~/Models/h3-apple/ref2va-lightx2v-v1` | `H3_MODEL_DIR` |
| Pika High | `~/Models/h3-apple/pika-ref2va` | `--model-dir` on the High generation call |

Set the variable in each session or pass `--model-dir`. Keep formats separate.
[X2 has its own directory](x2.md#model-preparation).

```sh
h3 prepare --reuse-dir /path/to/existing-models
```

Preparation defaults to VSA. Add `--mode SOL` for SOL, and repeat `--reuse-dir`
for multiple compatible sources.
[Model recipes](development.md) and licenses still apply.

</details>

<a name="upgrading-sol-models"></a>

<details>
<summary>Upgrade h3-apple or older SOL models</summary>

Activate `h3` and rerun the pip command with `--upgrade`.
Fast and Medium prepare LightX2V v1.0 in new default directories using the
shared original source cache. If a model-directory override points to v0.1,
set it to a v1.0 bundle or choose an empty destination. The old VSA directory
can still be passed to the [advanced four-step Dense replay](advanced.md).

**Old quantized SOL weights need fresh preparation.** Prepare a new directory:

```sh
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged --plan
h3 prepare --mode SOL --model-dir ~/Models/h3-apple-sol-premerged
```

To reuse original H3 weights and the matching v1.0 adapter, add `--reuse-dir /path/to/sources` to both
commands. Old quantized weights alone are insufficient. Pass the new `--model-dir`
on later SOL calls. Existing models are preserved.
[Recipe change](releases/0.7.0.md#fixes-you-can-see).

</details>

<details>
<summary>Troubleshooting</summary>

- `h3` not found: activate the environment or use `python -m h3_apple`.
- `h3 doctor` checks readiness; missing models before first use are expected.
- `h3 verify` checks all model checksums. Both default to VSA; use `--mode SOL` for SOL.
- Generation reserves 20 GiB temporary disk and stops on serious thermal pressure
  or swap growth above 2 GiB. Failed jobs retain logs.
- Native 768p over five seconds needs 96 GiB memory.
- High and advanced Dense attention require 128 GiB memory.

</details>

[Source installation](development.md#verify-a-change)
