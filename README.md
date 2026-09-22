# h3-apple

**Reference images + a prompt → video with stereo audio, locally on Mac.**

h3-apple focuses on making MiniMax-H3 fast and simple on Apple Silicon. One
Ref2VA generation path, with acceleration enabled automatically. Give it
1–9 images and describe the scene, movement and sound.

## Install

Use a dedicated Conda environment to keep H3's dependencies separate from your
other projects. If you do not have Conda, install the Apple Silicon version of
[Miniforge](https://github.com/conda-forge/miniforge) first.

```bash
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install https://github.com/RhinoQ/h3-apple/releases/download/v0.5.0/h3_apple-0.5.0-py3-none-any.whl
```

The release wheel is installed directly from GitHub.
Conda manages Python and FFmpeg together; pip installs h3-apple and Pillow in
that environment. The first generation automatically prepares the inference
engine and models, then continues to your video. Existing compatible models
are verified and reused. Python 3.11–3.14 is supported.

In a new terminal, run `conda activate h3` before using the CLI or Python API.

**Requirements:** an M5 Mac, macOS 26.2+, and at least 64 GB unified memory.
A first model preparation downloads about **145 GB** and needs about **233 GB**
free disk. The CLI shows the actual plan and asks before downloads over 20 GB.
Already prepared models take about **85 GB**. See [installation details](https://github.com/RhinoQ/h3-apple/blob/main/docs/install.md)
for an external disk, interrupted downloads or an existing model cache.

## Generate

```bash
h3 generate --image reference.jpg --prompt "The character in Picture 1 walks through a sunny park. Birds chirp and leaves rustle."
```

For multiple references and a complete storyboard:

```bash
h3 generate --image character.jpg --image style.jpg --prompt-file story.txt --output weekend.mp4
```

Images are numbered in the order supplied: `Picture 1`, `Picture 2`, and so on.
Describe how each reference should be used. The full prompt is passed through
unchanged. Style references may also influence characters and composition;
precise identity, text and shot timing are not guaranteed.

Defaults: **15 seconds, 576p, landscape, 24 fps, stereo audio**. Generated files
and their run records go into a new `runs/` folder unless `--output` is given.
Use `--duration 5` for a short first run, `--aspect-ratio 9:16` for portrait,
`--resolution 768p` for larger output, or `--seed 42` to record a fixed seed.
768p runs longer than 5 seconds require at least 96 GB memory.

```bash
h3 doctor
```

## Python

```python
import h3_apple

result = h3_apple.generate(
    prompt="Picture 1 and Picture 2 have a picnic at sunset. Birds and a soft breeze.",
    reference_images=["99.jpg", "bobo.jpg"],
    output="weekend.mp4",
)
print(result.video_path)
```

The API uses the same automatic setup and generation path. It never asks for
terminal input: if a first-time download exceeds 20 GB, it raises
`h3_apple.DownloadApprovalRequired` with the required sizes. Review them, then
repeat with `allow_large_download=True`. No flag is needed for prepared models.
Importing the package does not download models or start the engine.

If your shell cannot find `h3`, use `python -m h3_apple` with the Python that
installed the package. To upgrade, repeat the release-wheel installation command
with `--upgrade`.

[Python API](https://github.com/RhinoQ/h3-apple/blob/main/docs/api.md) · [Validation](https://github.com/RhinoQ/h3-apple/blob/main/docs/validation.md) · [Development and credits](https://github.com/RhinoQ/h3-apple/blob/main/docs/development.md)

## License

Built with MiniMax H3. This is an independent community project.
Code: [Apache-2.0](https://github.com/RhinoQ/h3-apple/blob/main/LICENSE); models: [MiniMax H3 Community License](https://github.com/RhinoQ/h3-apple/blob/main/licenses/MiniMax-H3.txt).
The integrated native engine and other upstream work retain their credits and
licenses in [THIRD_PARTY_NOTICES](https://github.com/RhinoQ/h3-apple/blob/main/THIRD_PARTY_NOTICES).

The [v0.3.0 release](https://github.com/RhinoQ/h3-apple/releases/tag/v0.3.0)
retains the earlier multi-task API, implementations and benchmark history.
