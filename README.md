# h3-apple

Turn 1–9 reference images and a prompt into a video with stereo sound on your Mac.
MiniMax-H3 generates 5–15 seconds at 24 fps, in landscape or portrait.

[Install](#install) · [Generate your first clip](#generate-a-video) · [What's new in 0.9.0](docs/releases/0.9.0.md)

**Wind It Up** · The 13-second h3-apple 0.9.0 release film

https://github.com/user-attachments/assets/8e2d6b82-bfd9-4837-a469-ca3ba6a70913

A die-cast rally car rolls across a paper map. Cut to the same red coupe on a snowy mountain pass.
Three original ImageGen stills guided three five-second **Pika High** shots on a 40-core M5 Max
with 128 GiB. The edit keeps the native **1366×768** frames and generated stereo sound, with a title added at the end.
[Watch with sound](https://rhinoq.github.io/h3-apple/?release=0.9.0#wind-it-up) · [Get the prompts, references, timings and commands](https://rhinoq.github.io/h3-apple/?release=0.9.0#wind-it-up~native~generation)

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

Save the sample as `apex.png`, or use one of your own images. [Download the rally-car reference](https://raw.githubusercontent.com/RhinoQ/h3-apple/15ceb7749aef752aa016e9b40723fb617facfbd1/features/wind-it-up/refs/apex.png)

```sh
h3 generate --image apex.png --output rally.mp4 \
  --prompt "The red coupe in Picture 1 slides around a snowy bend and accelerates past the camera. Its engine echoes across the valley."
```

Open `rally.mp4` to play the five-second clip. For portrait, add `--aspect-ratio 9:16`.
In a new terminal, run `conda activate h3` first.

**How long does it take?** Default Fast took **4m 27s** for five seconds of video
(median of eight scenes on a 40-core M5 Max with 128 GiB). That covers the full
generation call with prepared models, using LightX2V v1.0, VSA and the 544p + X2 decoder.
[Timings and quality choices](docs/advanced.md#performance) · [Python API](docs/api.md)

## Optional super-resolution

Double the width and height of a finished clip and keep its stereo audio.
VOSR writes a second MP4 and requires **128 GiB of unified memory** plus a **6.97 GB** model download.

```sh
h3 upscale --input rally.mp4 --output rally-2x.mp4
```

[Super-resolution examples, timings and noncommercial terms](docs/upscale.md)

---

h3-apple is an independent community project built on MiniMax-H3, LightX2V and Pika H3 Flex.
Our original code uses Apache-2.0. Model weights and third-party components carry their own terms.
[Credits](docs/development.md#implementation-and-credits) · [Code license](LICENSE) · [Model license](licenses/MiniMax-H3.txt) · [Third-party notices](THIRD_PARTY_NOTICES) · [Validation](docs/validation.md) · [Use with Codex](docs/advanced.md#use-with-codex)
