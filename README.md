# h3-apple

**Reference images + a prompt → video with stereo audio, locally on Mac.**

h3-apple generates MiniMax-H3 video from 1–9 images and a prompt describing the
scene, movement and sound. Version **0.7.0** adds optional [X2 decoding](docs/x2.md)
for landscape and portrait video. Both generation modes use
the original **LightX2V Ref2VA Turbo 4-step v0.1 LoRA**:

| Mode | Generation implementation |
| --- | --- |
| **VSA** (default) | MLX W8A8 projections, shared QKV activation packing, VSA and INT8 QK attention |
| **SOL** | Native INT8 GEMM, SOL attention and SageAttention; retains the 0.5.3 generation path |

Choose a mode explicitly when comparing results; the two implementations can
produce different images and sound with the same seed. See the
[mode details and validation](docs/validation.md). The prior original-LightX2V
[99/bobo comparison](https://rhinoq.github.io/h3-apple/previews/99-bobo-lora-v052/)
remains available.

Optional **X2 decoding** doubles output width and height. Use 544p sampling for
lower denoising cost, or native 768p sampling for larger output. This feature is
available in the 0.7.0 source checkout; the published release below remains 0.6.0.
Install the checkout inside your Conda environment with `python -m pip install ".[VSA]"`.
See [X2 examples, model setup and quality limits](docs/x2.md).

Optional **small-face enhancement** is available for finished videos.
It automatically selects small face tracks, enhances their local detail and
preserves the source audio. Both generation modes use four denoising steps.
Enhancement is an additional operation,
with separately installed dependencies and models. See the
[preview, setup and limits](docs/face-enhancement.md) and
[generation measurements](docs/validation.md).

## Install

Use a dedicated Conda environment to keep H3's dependencies separate from your
other projects. If you do not have Conda, install the Apple Silicon version of
[Miniforge](https://github.com/conda-forge/miniforge) first.

Install the [0.6.0 release](https://github.com/RhinoQ/h3-apple/releases/tag/v0.6.0)
with both generation modes:

```bash
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.6.0/h3_apple-0.6.0-py3-none-any.whl"
```

For SOL alone, omit `[VSA]` from the installation requirement; select it with
`--mode SOL` or `mode="SOL"`. VSA adds pinned MLX, PyTorch and Transformers
dependencies and requires Python 3.11. SOL supports Python 3.11–3.14.

Conda manages Python and FFmpeg together. The first generation prepares the
selected mode's models, then continues to your video. Existing compatible
models are verified and reused.

In a new terminal, run `conda activate h3` before using the CLI or Python API.

**Requirements:** a 40-core M5 Max, macOS 26.2+, and at least 64 GB unified memory.
This release was tested on 128 GB; smaller-memory machines have not been validated.
A fresh SOL model preparation downloads about **145 GB**; VSA needs about
**151 GB**. Prepared models occupy about **85 GB** for SOL or **111 GB** for VSA
when duplicate files share hard links. Run `h3 prepare --mode VSA --plan` or
`h3 prepare --mode SOL --plan` for actual download and disk requirements.
The CLI asks before downloads over 20 GB. See [installation details](docs/install.md)
for reuse, mode-specific model locations and disk requirements.

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

The optional [Codex video skill](#codex-video-skill) can handle setup, prompt
writing and generation from your references and creative brief.

Defaults: **VSA, 15 seconds, 576p, landscape, 24 fps, stereo audio**. Generated files
and their run records go into a new `runs/` folder unless `--output` is given.
Use `--duration 5` for a short first run, `--aspect-ratio 9:16` for portrait,
`--resolution 768p` for larger output, or `--seed 42` to record a fixed seed.
768p runs longer than 5 seconds require at least 96 GB memory.

```bash
h3 generate --mode VSA --image reference.jpg --prompt-file story.txt --seed 42 --output VSA.mp4
h3 generate --mode SOL --image reference.jpg --prompt-file story.txt --seed 42 --output SOL.mp4
h3 doctor --mode VSA
h3 doctor --mode SOL
```

Use the same `--seed`, references and prompt to compare the modes. Each has its
own model bundle; `--model-dir` selects the bundle for the requested mode.

## Codex video skill

The [Ref2VA skill](skills/h3-apple-ref2va-prompting/SKILL.md) checks for h3-apple,
reuses a compatible installation or installs missing components in an isolated
Conda environment, then plans the prompt, generates the video and reviews the
result. Downloads over 20 GB require your consent. It works across subjects and
video styles.

To install it, paste this into a [Codex chat](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use):

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/main/skills/h3-apple-ref2va-prompting
```

Then attach your reference images and invoke it in your next message:

```text
$h3-apple-ref2va-prompting
Create a 5-second video from these images, with Mandarin dialogue and no subtitles.
Save the finished video as demo.mp4.
```

For a prompt or storyboard only, say so; the skill will skip installation and
generation. If you already installed an older skill, ask Codex to update it from
the same repository path. If the skill does not appear, restart Codex.

## Python

```python
import h3_apple

result = h3_apple.generate(
    prompt="Picture 1 and Picture 2 have a picnic at sunset. Birds and a soft breeze.",
    reference_images=["99.jpg", "bobo.jpg"],
    output="weekend.mp4",
    mode="VSA",  # default; use "SOL" for the other mode
)
print(result.video_path)
```

The API uses the same automatic setup and generation path. It never asks for
terminal input: if a first-time download exceeds 20 GB, it raises
`h3_apple.DownloadApprovalRequired` with the required sizes. Review them, then
repeat with `allow_large_download=True`. No flag is needed for prepared models.
Importing the package does not download models or start the engine.

## Optional face enhancement

After the [one-time optional setup](docs/face-enhancement.md):

```bash
h3 enhance-faces --input weekend.mp4 --output weekend-enhanced.mp4
```

This uses VOSR2 on automatically selected small faces. It keeps the video size,
frame rate and original audio; large closeups are skipped. Inspect the result:
restored eye, mouth and skin detail can change, and the model has no temporal
conditioning. It cannot fix acting, gaze direction or story continuity.

If your shell cannot find `h3`, use `python -m h3_apple` with the Python that
installed the package. To upgrade, repeat the installation command above with `--upgrade`.

[Python API](https://github.com/RhinoQ/h3-apple/blob/main/docs/api.md) · [Validation](https://github.com/RhinoQ/h3-apple/blob/main/docs/validation.md) · [Development and credits](https://github.com/RhinoQ/h3-apple/blob/main/docs/development.md)

## License

Built with MiniMax H3. This is an independent community project.
Independently authored code: [Apache-2.0](https://github.com/RhinoQ/h3-apple/blob/main/LICENSE);
generation models: [MiniMax H3 Community License](https://github.com/RhinoQ/h3-apple/blob/main/licenses/MiniMax-H3.txt).
The optional restoration components have separate terms, including the retained
Llama 2 normalization component and the CC BY-NC DiT source lineage. The combined
package is not offered under an Apache-only commercial-use grant. See the
[component terms](docs/face-enhancement.md#component-terms).
The integrated native engine and other upstream work retain their credits and
licenses in [THIRD_PARTY_NOTICES](https://github.com/RhinoQ/h3-apple/blob/main/THIRD_PARTY_NOTICES).

The [v0.3.0 release](https://github.com/RhinoQ/h3-apple/releases/tag/v0.3.0)
retains the earlier multi-task API, implementations and benchmark history.
