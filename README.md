# h3-apple

**A 5-second video with sound in about 3 minutes. On your Mac.**

Turn 1–9 images and a prompt into video with stereo audio. Landscape or portrait,
5–15 seconds. Powered by MiniMax-H3.

**3m 14s median** at default settings on a 40-core M5 Max / 128 GiB:
12 scenes, after model setup. [Measured settings and performance](docs/advanced.md#performance).

[**Watch the videos →**](https://rhinoq.github.io/h3-apple/#showcase) ·
[**Install →**](#1-install) · [**What's new →**](docs/releases/0.8.2.md)

| Celestial Hall | Stairway Above the Clouds |
| --- | --- |
| [![Sunlight and silk in a celestial hall](https://rhinoq.github.io/h3-apple/assets/showcase/n8.jpg)](https://rhinoq.github.io/h3-apple/#showcase-N8) | [![A golden stairway rising through a sea of clouds](https://rhinoq.github.io/h3-apple/assets/showcase/n6.jpg)](https://rhinoq.github.io/h3-apple/#showcase-N6) |

Showcase: native 768p + VOSR 2×, **2732×1536**. Super-resolution adds about
**20 minutes per five-second clip**, beyond generation. [Prompts and settings](https://rhinoq.github.io/h3-apple/#showcase).

<a name="install"></a>

## 1. Install

**40-core M5 Max · macOS 26.2+ · 64 GiB minimum.** Tested with 128 GiB;
smaller-memory operation is unverified. Fresh setup needs about
**150 GB of downloads and 241 GB of free disk**.

Install [Miniforge](https://github.com/conda-forge/miniforge#miniforge3) if you need Conda, then run:

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple @ https://github.com/RhinoQ/h3-apple/releases/download/v0.8.2/h3_apple-0.8.2-py3-none-any.whl"
```

First use prepares models and asks before downloads over 20 GB.
In each new terminal, run `conda activate h3`. [Installation help](docs/install.md).

<a name="generate"></a>

## 2. Generate

Replace `reference.jpg` with your image path:

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on the scene in Picture 1. Soft ambient music."
```

This creates a **five-second video** in a new `runs/` folder and prints its path.
Choose `--quality fast`, `--quality medium` or `--quality high`:

| Quality | Use it for |
| --- | --- |
| `fast` (default) | The quickest generation |
| `medium` | Native 768p output |
| `high` | Dense generation with 2× restoration; requires 128 GiB and takes longer |

Add `--aspect-ratio 9:16` for portrait. Set any **5–15-second duration** aligned
to a frame at 24 fps, such as `--duration 7` or `--duration 8.5`.
High saves both the native and restored videos and uses the
[super-resolution models and noncommercial terms](docs/upscale.md).

[Advanced settings](docs/advanced.md) · [Python API](docs/api.md)

## 3. Optional super-resolution

Add detail to a video you have already generated. Use its saved path:

```sh
h3 upscale --input video.mp4
```

Works with default output, doubles its dimensions, and preserves the original
video and audio. Requires **128 GiB memory** and a separate **6.97 GB** model
download. Restoration takes tens of minutes per five-second clip, depending on
input size; it is separate from the generation time above.

[Super-resolution guide and noncommercial terms](docs/upscale.md)

---

[Use with Codex](docs/advanced.md#use-with-codex) ·
[Development and community credits](docs/development.md#implementation-and-credits) ·
[Validation](docs/validation.md)

Independent community project. Original code: [Apache-2.0](LICENSE).
Models: [MiniMax H3 Community License](licenses/MiniMax-H3.txt).
Third-party code keeps its [own terms](THIRD_PARTY_NOTICES); super-resolution
includes components restricted to noncommercial use.
