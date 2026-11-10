# h3-apple

Turn 1–9 reference images and a prompt into a video with stereo sound on your Mac.
MiniMax-H3 generates 5–15 seconds at 24 fps, in landscape or portrait.

[Watch the 0.9.0 gallery](https://rhinoq.github.io/h3-apple/?release=0.9.0) · [Install](#install) · [What's new in 0.9.0](docs/releases/0.9.0.md)

[![Four frames from the fan film show the same pink rabbit in a trench coat, floral skirt, blue dress and denim with a burgundy bow](docs/media/four-looks-under-the-fan.jpg)](https://rhinoq.github.io/h3-apple/?release=0.9.0#fan-wardrobe~2x)

**Four looks under the fan** is a 15-second film made from three five-second Pika High shots.
The stills show the optional 1536×2732 VOSR 2× version. The gallery includes the native
768×1366 film, every prompt and reference, and the commands behind each shot.
[Watch the film](https://rhinoq.github.io/h3-apple/?release=0.9.0#fan-wardrobe~2x) · [See how it was made](https://rhinoq.github.io/h3-apple/?release=0.9.0#fan-wardrobe~2x~generation)

## Install

Use a **40-core Apple M5 Max** with **macOS 26.2 or later** and at least **64 GiB of unified memory**.
We tested on 128 GiB. A fresh default setup needs about **156 GB of downloads**
and **351 GB of free disk**. First use shows the download estimate and asks before transfers above 20 GB.

Use Conda to install the release. [Get Miniforge for Apple Silicon](https://github.com/conda-forge/miniforge#miniforge3) · [Installation guide](docs/install.md)

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install https://github.com/RhinoQ/h3-apple/releases/download/v0.9.0/h3_apple-0.9.0-py3-none-any.whl
```

## Generate a video

Save the sample as `rabbit.png`, or substitute your own image path. [Download the rabbit reference](https://raw.githubusercontent.com/RhinoQ/h3-apple/885a874c76664d0781337950d9ddc6ece0ee548e/features/fan-wardrobe/refs/01-rest-3d.png)

```sh
h3 generate --image rabbit.png --output rabbit.mp4 \
  --prompt "The pink rabbit in Picture 1 raises one paw and waves. Its coat rustles."
```

Open `rabbit.mp4` to play the five-second clip. For portrait, add `--aspect-ratio 9:16`.
In a new terminal, run `conda activate h3` first.

**How long does it take?** Default Fast took **4m 27s** for five seconds of video
(median of eight scenes on a 40-core M5 Max with 128 GiB). That covers the full
generation call with prepared models, using LightX2V v1.0, VSA and the 544p + X2 decoder.
[Timings and quality choices](docs/advanced.md#performance) · [Python API](docs/api.md)

## Optional super-resolution

Double the width and height of a finished clip and keep its stereo audio.
VOSR writes a second MP4 and requires **128 GiB of unified memory** plus a **6.97 GB** model download.

```sh
h3 upscale --input rabbit.mp4 --output rabbit-2x.mp4
```

Restoring the 15-second fan film took **53m 58s** on the 40-core M5 Max with 128 GiB,
after **1h 01m 52s** of native Pika generation for the three selected shots.
[Film timings](https://rhinoq.github.io/h3-apple/?release=0.9.0#fan-wardrobe~2x~generation) · [Super-resolution guide and noncommercial terms](docs/upscale.md)

---

h3-apple is an independent community project built on MiniMax-H3, LightX2V and Pika H3 Flex.
Our original code uses Apache-2.0. Model weights and third-party components carry their own terms.
[Credits](docs/development.md#implementation-and-credits) · [Code license](LICENSE) · [Model license](licenses/MiniMax-H3.txt) · [Third-party notices](THIRD_PARTY_NOTICES) · [Validation](docs/validation.md) · [Use with Codex](docs/advanced.md#use-with-codex)
