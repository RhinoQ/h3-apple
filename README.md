# h3-apple

**A 5-second video with sound in about 3 minutes. On your Mac.**

Turn 1–9 images and a prompt into 5–15 seconds of video with stereo audio.
Powered by MiniMax-H3. Landscape or portrait, CLI or Python.

Generate fast with SOL + X2. Add finer detail with VOSR super-resolution.
One Mac workflow, from reference images to finished video.
[What's new in 0.8.0](docs/releases/0.8.0.md).

**3m 14s median** with SOL + 544p/X2 on a 40-core M5 Max / 128 GiB:
12 scenes, full API calls after model setup in the 0.7.0 benchmark.

[**Watch the videos →**](https://rhinoq.github.io/h3-apple/#showcase) ·
[**Install →**](#install) · [**0.8.0 release →**](docs/releases/0.8.0.md)

| Celestial Hall | Stairway Above the Clouds |
| --- | --- |
| [![Sunlight and silk in a celestial hall](https://rhinoq.github.io/h3-apple/assets/showcase/n8.jpg)](https://rhinoq.github.io/h3-apple/#showcase-N8) | [![A golden stairway rising through a sea of clouds](https://rhinoq.github.io/h3-apple/assets/showcase/n6.jpg)](https://rhinoq.github.io/h3-apple/#showcase-N6) |

Showcase: native 768p + VOSR 2×, **2732×1536**. Super-resolution adds about
**20 minutes per five-second clip**, beyond generation. [Prompts and settings](https://rhinoq.github.io/h3-apple/#showcase).

## Performance

Median time per five-second video on the Mac above:

| Mode | Native 768p | 544p + X2 | Tradeoff in this test |
| --- | ---: | ---: | --- |
| **VSA** | 8m 49s | **4m 19s** | Less memory; fewer geometry defects |
| **SOL**, default | 6m 04s | **3m 14s** | Faster; better framing |

X2 delivers **2.07× VSA / 1.91× SOL** median speedups within matched scenes.
One run per configuration; quality varies by scene.
[See all 48 videos, scores and inputs](https://rhinoq.github.io/h3-apple/#results).

## Install

**40-core M5 Max · macOS 26.2+ · 64 GiB minimum.** Tested with 128 GiB;
smaller-memory operation is unverified. Fresh SOL + X2 setup needs about
**150 GB of downloads and 241 GB of free disk**.

Install [Miniforge](https://github.com/conda-forge/miniforge#miniforge3) if you need Conda, then run:

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple @ https://github.com/RhinoQ/h3-apple/releases/download/v0.8.0/h3_apple-0.8.0-py3-none-any.whl"
```

First use prepares models and asks before downloads over 20 GB.
[Model storage and upgrades](docs/install.md).

## Generate

Default: **SOL + 544p/X2**. Replace `reference.jpg` with your image path:

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music." \
  --duration 5 --output first-video.mp4
```

Open `first-video.mp4`. Use a new output name each time.
Run `conda activate h3` in each new terminal.

| Option | Flag |
| --- | --- |
| Portrait | `--aspect-ratio 9:16` |
| Native 768p | `--resolution 768p --no-x2`; over five seconds needs 96 GiB |
| VSA mode | `--mode VSA` |
| Prompt file | `--prompt-file scene.txt` instead of `--prompt` |
| More references | Repeat `--image` in Picture order |

### Output

X2 delivers **1920×1088 landscape or 1088×1920 portrait** while generating at 544p
for speed. Detail and motion can vary; use the [benchmark](https://rhinoq.github.io/h3-apple/)
to compare output quality. [Settings and examples](docs/x2.md).

### Python

```python
from h3_apple import generate

result = generate(
    prompt="A slow push-in on Picture 1. Soft ambient music.",
    reference_images=["reference.jpg"], duration=5, output="scene.mp4",
)
print(result.video_path)
```

[API settings and first-download consent](docs/api.md)

## Add detail with super-resolution

Generate at native 768p with `--resolution 768p --no-x2`, then run:

```sh
h3 upscale --input native.mp4 --output detailed.mp4
```

VOSR doubles width and height while preserving audio. Requires **128 GiB memory**
and a separate **6.97 GB** model download. [Super-resolution guide and terms](docs/upscale.md).

## Use with Codex

Install the [Ref2VA skill](skills/h3-apple-ref2va-prompting/SKILL.md):

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/main/skills/h3-apple-ref2va-prompting
```

Attach images and invoke `$h3-apple-ref2va-prompting` with your brief.

[Development](docs/development.md) · [Validation](docs/validation.md) ·
[Community credits](docs/releases/0.8.0.md#what-we-built)

## License

Independent community project. Original code: [Apache-2.0](LICENSE).
Models: [MiniMax H3 Community License](licenses/MiniMax-H3.txt).
Third-party code keeps its [own terms](THIRD_PARTY_NOTICES); VOSR includes
components restricted to noncommercial use.
