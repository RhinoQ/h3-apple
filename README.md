# h3-apple

**Create a 5-second video with sound in about 3 minutes. On your Mac.**

**3m 14s median** on a 40-core M5 Max / 128 GiB, using SOL at **544p + X2**
across twelve scenes. Full generation calls with prepared models; first-time
downloads and setup are excluded. Native 768p takes longer; see the comparison below.

[**Watch the videos →**](https://rhinoq.github.io/h3-apple/#library) ·
[**Install →**](#install) ·
[**Get 0.7.0 →**](https://github.com/RhinoQ/h3-apple/releases/tag/v0.7.0)

Give MiniMax-H3 1–9 reference images and a prompt. Get 5–15 seconds of video with
stereo audio, in landscape or portrait. Generation runs locally through a CLI or
Python API, with two modes to trade speed, memory and scene quality.

[![Cloud-palace video preview: a blue-and-gold palace above the clouds](https://rhinoq.github.io/h3-apple/assets/posters/060f8e72ff066feda2174e16334d06862108b09746c788e8586b13ae9e584cdd.jpg)](https://rhinoq.github.io/h3-apple/#case=cloud-palace)

*Watch the five-second cloud-palace example. The benchmark includes all 48 outputs,
exact prompts, reference images and replay instructions.*

## Speed you can check

Median time per **5-second video**, on the same M5 Max / 128 GiB:

| Mode | Standard · native 768p | Fast · 544p + X2 | Why choose it? |
| --- | ---: | ---: | --- |
| **VSA**, default | 8m 49s | **4m 19s** | Lower memory use; fewer clear geometry defects in this set |
| **SOL** | 6m 04s | **3m 14s** | Faster generation; better framing in this set |

**X2 roughly halves generation time:** 2.07× for VSA and 1.91× for SOL, using
the median of within-scene speed ratios. Twelve scenes, one run per route;
quality varies by scene. [Compare speed, memory and quality →](https://rhinoq.github.io/h3-apple/#results)

Fast mode samples at 544p and decodes to 1920×1088 landscape or 1088×1920 portrait.
Standard mode delivers 1366×768 or 768×1366. X2 adds pixels; it cannot repair a
failed action or composition. [0.7.0 release notes](docs/releases/0.7.0.md) explain
the acceleration over 0.6.0, SOL fixes and community contributions.

## Install

Requires a **40-core M5 Max, macOS 26.2+ and at least 64 GiB memory**.
Measurements used 128 GiB; smaller-memory operation is unverified.
Fresh VSA setup needs about **151 GB of downloads and 343 GB of free disk**.
Use Conda, or install [Miniforge for Apple Silicon](https://github.com/conda-forge/miniforge#miniforge3) first.

One installation supports **VSA, SOL and X2**:

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
```

First use prepares the selected mode's models and asks before large downloads.
In a new terminal, run `conda activate h3`. [Setup details and upgrades →](docs/install.md)

## Generate

Replace `reference.jpg` with your image path. This makes a **five-second video
with sound** using the default VSA mode:

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music." \
  --duration 5 --output first-video.mp4
```

Open `first-video.mp4` when it finishes. Initial setup takes extra time;
later runs reuse the models. Use a new output filename each time.

| To change… | Use… |
| --- | --- |
| Portrait | `--aspect-ratio 9:16` |
| Native 768p | `--resolution 768p`; beyond five seconds requires 96 GiB |
| Prompt from a file | `--prompt-file scene.txt` instead of `--prompt` |

Repeat `--image` for up to nine references in `Picture 1`, `Picture 2` order.
Defaults: VSA, 15 seconds, 576p, landscape, 24 fps, stereo 32 kHz.
[All settings and seeds →](docs/api.md)

### Faster generation

Use the **SOL + 544p/X2 benchmark configuration** (3m 14s median on M5 Max / 128 GiB):

```sh
h3 generate --mode SOL --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music." \
  --duration 5 --resolution 544p --x2 --output fast-video.mp4
```

Run this directly after installation: SOL + X2 prepares its own models automatically.
VSA models are not required. [Check download and disk costs →](docs/install.md#optional-setup)

Use `--mode VSA` for lower memory use; `--aspect-ratio 9:16` for portrait.
[X2](docs/x2.md) accepts 544p or 576p; 768p + X2 is unsupported.
Inspect motion, small faces, text and geometry. [Face enhancement](docs/face-enhancement.md)
is a separate optional step.

### Python

```python
from h3_apple import generate

result = generate(
    prompt="Picture 1 walks through a sunny park. Birds chirp and leaves rustle.",
    reference_images=["reference.jpg"],
    duration=5,
    output="scene.mp4",
)
print(result.video_path)
```

Prepared models are reused. The Python API raises `DownloadApprovalRequired`
before a large first-time download; review the plan before enabling
`allow_large_download=True`. See the [API contract](docs/api.md).

## Codex video skill

The [Ref2VA skill](skills/h3-apple-ref2va-prompting/SKILL.md) handles local setup,
prompts, generation and review. Install it in Codex:

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/main/skills/h3-apple-ref2va-prompting
```

Then attach images and invoke `$h3-apple-ref2va-prompting` with your brief.

[Installation](docs/install.md) · [API](docs/api.md) · [Validation](docs/validation.md) ·
[Development](docs/development.md) · [Community contributions](docs/releases/0.7.0.md#what-comes-from-the-community-and-what-we-contributed)

## License

Independent community project built with MiniMax H3. Original code is
[Apache-2.0](LICENSE); generation models use the [MiniMax H3 Community License](licenses/MiniMax-H3.txt).
Upstream code retains its licenses and [notices](THIRD_PARTY_NOTICES).
Optional restoration has [additional component terms](docs/face-enhancement.md#component-terms),
including Llama 2 and CC BY-NC source lineage; the combined package has no
Apache-only commercial-use grant.
