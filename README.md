# h3-apple

**Reference images + a prompt → video with stereo audio, locally on Mac.**

h3-apple focuses on making MiniMax-H3 fast and simple on Apple Silicon. One
Ref2VA generation path, with acceleration enabled automatically. Give it
1–9 images and describe the scene, movement and sound.

Version **0.5.3** uses the original **LightX2V Ref2VA Turbo 4-step v0.1 LoRA**.
The 99/bobo comparison showed less motion ghosting in running and bread handoff,
with some blur remaining. [Watch the comparison](https://rhinoq.github.io/h3-apple/previews/99-bobo-lora-v052/)
and see the [validation scope](docs/validation.md).

Optional **small-face enhancement** is available for finished videos.
It automatically selects small face tracks, enhances their local detail and
preserves the source audio. Generation uses the existing four-step native engine.
Enhancement is an additional operation,
with separately installed dependencies and models. See the
[preview, setup and limits](docs/face-enhancement.md) and
[generation measurements](docs/validation.md).

## Install

Use a dedicated Conda environment to keep H3's dependencies separate from your
other projects. If you do not have Conda, install the Apple Silicon version of
[Miniforge](https://github.com/conda-forge/miniforge) first.

```bash
conda create -n h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3
python -m pip install https://github.com/RhinoQ/h3-apple/releases/download/v0.5.3/h3_apple-0.5.3-py3-none-any.whl
```

The release wheel is installed directly from GitHub.
Conda manages Python and FFmpeg together; pip installs h3-apple and Pillow in
that environment. The first generation automatically prepares the inference
engine and models, then continues to your video. Existing compatible models
are verified and reused. Python 3.11–3.14 is supported.

In a new terminal, run `conda activate h3` before using the CLI or Python API.

**Requirements:** a 40-core M5 Max, macOS 26.2+, and at least 64 GB unified memory.
This release was tested on 128 GB; smaller-memory machines have not been validated.
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

The optional [Codex prompting skill](#prompting-skill-for-codex) helps turn your
references and creative brief into a complete prompt.

Defaults: **15 seconds, 576p, landscape, 24 fps, stereo audio**. Generated files
and their run records go into a new `runs/` folder unless `--output` is given.
Use `--duration 5` for a short first run, `--aspect-ratio 9:16` for portrait,
`--resolution 768p` for larger output, or `--seed 42` to record a fixed seed.
768p runs longer than 5 seconds require at least 96 GB memory.

```bash
h3 doctor
```

## Prompting skill for Codex

The [Ref2VA prompting skill](skills/h3-apple-ref2va-prompting/SKILL.md) helps plan
reference roles, shots and audio, and review motion, visible text and continuity.
It works across subjects and video styles.

To install it, paste this into a [Codex chat](https://learn.chatgpt.com/docs/build-skills#install-curated-skills-for-local-use):

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/v0.5.3/skills/h3-apple-ref2va-prompting
```

Then attach your reference images and invoke it in your next message:

```text
$h3-apple-ref2va-prompting
Plan a 5-second video from these images, with Mandarin dialogue and no subtitles.
Save the complete prompt as story.txt.
```

Use the [generation command above](#generate) with `--prompt-file story.txt --duration 5`,
keeping the images in the order used by the prompt. If the skill does not appear,
restart Codex. A standalone [skill ZIP](https://github.com/RhinoQ/h3-apple/releases/download/v0.5.3/h3-apple-ref2va-prompting.zip)
is also available.

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
installed the package. To upgrade, repeat the release-wheel installation command
with `--upgrade`.

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
