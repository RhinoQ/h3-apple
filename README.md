# h3-apple

**Reference images + a prompt → video with stereo audio, locally on Mac.**

h3-apple focuses on making MiniMax-H3 fast and simple on Apple Silicon. One
Ref2VA generation path, with acceleration enabled automatically. Give it
1–9 images and describe the scene, movement and sound.

## Install

Download and unzip the [latest release](https://github.com/RhinoQ/h3-apple/releases/latest),
open a terminal in its folder, and run:

```bash
./install.sh
```

The installer sets up a private Conda environment, media tools, the inference
engine and models. No environment activation, separate engine installation or
mode selection is needed. Existing compatible models are verified and reused.

**Requirements:** an M5 Mac, macOS 26.2+, and at least 64 GB unified memory.
A first model preparation downloads about **145 GB** and needs about **233 GB**
free disk; the installer shows the actual plan and asks before large downloads.
Already prepared models take about **85 GB**. See [installation details](docs/install.md)
for an external disk, interrupted downloads or an existing model cache.

## Generate

```bash
./h3 generate --image reference.jpg --prompt "The character in Picture 1 walks through a sunny park. Birds chirp and leaves rustle."
```

For multiple references and a complete storyboard:

```bash
./h3 generate --image character.jpg --image style.jpg --prompt-file story.txt --output weekend.mp4
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
./h3 doctor
```

[Python API](docs/api.md) · [Validation](docs/validation.md) · [Development and credits](docs/development.md)

## License

Built with MiniMax H3. This is an independent community project.
Code: [Apache-2.0](LICENSE); models: [MiniMax H3 Community License](licenses/MiniMax-H3.txt).
The integrated native engine and other upstream work retain their credits and
licenses in [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).

The [v0.3.0 release](https://github.com/RhinoQ/h3-apple/releases/tag/v0.3.0)
retains the earlier multi-task API, implementations and benchmark history.
