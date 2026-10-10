# h3-apple

**Reference images + a prompt → video with stereo audio, locally on Mac.**

Generate 5–15 second MiniMax-H3 videos from 1–9 ordered images. Both modes use
the original LightX2V Ref2VA Turbo four-step v0.1 adapter.

| Mode | Implementation |
| --- | --- |
| **VSA**, default | MLX W8A8 projections, shared QKV activation packing, VSA and INT8 QK |
| **SOL** | Native INT8 GEMM, SOL and SageAttention; Turbo merged before W8G64 preparation |

**[Version 0.7.0](https://github.com/RhinoQ/h3-apple/releases/tag/v0.7.0)** adds
544p/576p + X2 in both orientations and corrects SOL's Turbo preparation.
In the twelve-case [benchmark](https://rhinoq.github.io/h3-apple/), 544p + X2
takes about half the native-768p time: 2.07× for VSA and 1.91× for SOL.
These are paired single-run ratios, with scene-dependent quality tradeoffs.
See [installation](docs/install.md) and [release notes](docs/releases/0.7.0.md)
for setup, evidence and community credits.

## Install

Requirements: **40-core M5 Max, macOS 26.2+, 64 GiB memory**, with a dedicated
Conda environment. Measurements used 128 GiB; smaller configurations are unverified.
768p beyond five seconds requires 96 GiB.

Install VSA and the shared X2 dependencies:

```sh
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
h3 doctor --mode VSA
```

SOL additionally needs the [matching native engine and prepared models](docs/install.md).
Fresh generation-model downloads are approximately 151 GB for VSA or 145 GB for
SOL. Check `h3 prepare --mode VSA --plan` first. Downloads above 20 GB require
consent. Installation and import do not download models.

## Generate

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --duration 5 --output scene.mp4
h3 generate --mode SOL --image reference.jpg --prompt-file scene.txt --duration 5 --output scene-sol.mp4
```

Repeat `--image` to supply `Picture 1`, `Picture 2`, etc. Order and prompt text
are preserved. Defaults are VSA, 15 seconds, 576p, landscape, 24 fps and stereo
32 kHz audio. Use `--aspect-ratio 9:16` for portrait, `--resolution 768p` for
ordinary larger output, or `--seed 42` for a recorded seed. The same seed can
produce different results across modes.

For lower sampling cost, use [X2](docs/x2.md):

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --duration 5 \
  --resolution 544p --x2 --aspect-ratio 9:16 --output portrait-x2.mp4
```

X2 accepts 544p or 576p in either orientation and doubles decoded dimensions.
768p + X2 is unsupported. Inspect motion, small faces, text and geometry: extra
pixels do not repair an incorrect sampled scene. [Optional face enhancement](docs/face-enhancement.md)
is a separate operation on finished videos.

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
