# Generation API

The CLI and Python interface share `generate()` and the versioned `ours` recipe.
Each generation runs in a separate worker process and releases model memory
when it exits. No persistent service is required.

```python
from h3_apple import generate, resolve

request = resolve("A quiet bakery opens at dawn. Gentle bells and birdsong.", duration=5, seed=87001)
print(request.to_dict())  # Does not load MLX or model weights.

result = generate(
    prompt="A quiet bakery opens at dawn. Gentle bells and birdsong.",
    resolution="768p",
    duration=5,
    seed=87001,
    output="bakery.mp4",
    on_progress=lambda event: print(event),
)
print(result.video_path)
print(result.metadata_path)
print(result.elapsed_seconds)
```

| Python parameter | CLI | Behavior |
| --- | --- | --- |
| `prompt` / `prompt_file` | `--prompt` / `--prompt-file` | Supply exactly one; accepts arbitrary UTF-8 prompt text |
| `preset="ours"` | `--preset ours` | The supported recipe; records its version, code, and model identity |
| `task=None` | `--task t2va/fl2va/ref2va` | Inferred from inputs when omitted; an explicit task must match the inputs and model bundle |
| `first_frame` / `last_frame` | `--first-frame` / `--last-frame` | FL2VA still-image anchors; either one or both; cannot mix with Ref2VA references |
| `resolution=None` | `--resolution 768p` | `768p` or `576p`; defaults to 768p, or 576p for image-only Ref2VA |
| `aspect_ratio="16:9"` | `--aspect-ratio 9:16` | Landscape `16:9` (default) or portrait `9:16`; applies to all three tasks |
| `reference_images=None` | Repeat `--reference-image /path` | Ordered list of 1–9 still images; requires a dedicated Ref2VA bundle |
| `reference_videos=None` | Repeat `--reference-video /path` | Ordered list of 1–3 local 2–15s videos, optionally with images; uses the same Ref2VA bundle |
| `reference_audio=None` | Repeat `--reference-audio /path` | Ordered list of 1–3 local 2–15s mono/stereo audio files; requires a Ref2VA image or video |
| `reference_video_audio=True` | `--no-reference-video-audio` | Disable all reference-video soundtracks while keeping explicit audio files; requires a video |
| `reference_resize="legacy"` | `--reference-resize match` | Ref2VA images only: opt into the target canvas's pixel area; legacy keeps the previous 258,048-pixel budget |
| `duration=15` | `--duration 15` | 5–15 seconds, corresponding to an integer number of frames at 24 fps |
| `seed=None` | `--seed 87001` | Generated and recorded when omitted; range 0–4294967295 |
| `output=None` | `--output bakery.mp4` | Creates a unique output directory by default; an explicit path gets an adjacent `bakery.run.json`; refuses overwrites |
| `model_dir=None` | `--model-dir /path` | Uses `$H3_MODEL_DIR`, otherwise `~/Models/h3-apple` |
| `on_progress=None` | Progress bar on stderr; `--no-progress` disables it | Callback receives stage and denoising/decoding events; stdout holds the final JSON |
| `timeout=7200` | `--timeout 7200` | Stops the process group on timeout and preserves the failure record |
| `diagnostics=False` | `--diagnostics` | Research tensors, raw pixels, and audio; uses substantial storage and increases waiting time |

`GenerationResult` exposes `video_path`, `metadata_path`, `elapsed_seconds`, and
`seed`. `GenerationRequest` is a frozen dataclass; `to_dict()` shows the resolved
specification. The public exports are `generate`, `resolve`,
and `GenerationResult` from `h3_apple`. For request type annotations, import
`GenerationRequest` from `h3_apple.api`.

On 64 GiB machines, generation admits 768p / 5 seconds and 576p / 5–15 seconds.
Longer 768p requests require at least 96 GiB and return an error with smaller
alternatives before model loading. `resolve()` describes geometry without
checking the current host; `generate()` enforces the memory boundary. See the
[hardware validation and limits](../README.md#hardware-and-memory) before
using a new machine; budget validation does not establish physical 64 GB support.
Those memory-budget tests cover text generation. Ref2VA image cases cover
one and four images at 576p on M5 Max / 128 GiB; other image counts, 768p
image-reference generation and smaller memory capacities do not yet have
equivalent validation. [Video-reference validation](ref2va-video.md) has its
own limited scope and does not extend those memory-budget results.

## Portrait output

Choose `--aspect-ratio 9:16` or `aspect_ratio="9:16"` to generate on a portrait
canvas. This applies to T2VA, FL2VA and every Ref2VA reference combination.
The default remains landscape, including when the reference input is portrait.
Input images and videos retain their existing task-specific preparation.

```bash
h3 generate --task fl2va --prompt-file prompt.txt --first-frame poster.png --model-dir ~/Models/h3-apple-fl2va-v12 --aspect-ratio 9:16 --resolution 768p --duration 5 --seed 42 --output portrait.mp4
```

```python
request = resolve(
    "A portrait shot of a woman beside a lake, with quiet water sounds.",
    aspect_ratio="9:16", resolution="768p", duration=5, seed=42,
)
assert (request.width, request.height) == (768, 1366)
```

At 768p, the model generates 768×1376 pixels and delivery removes five rows
from each end of the height. At 576p, both canvases are 576×1024.
This generates portrait frames directly; it does not rotate or stretch a
landscape video after generation. The run record retains the actual delivery
and model dimensions. Model weights, steps, attention and audio settings follow
the selected task as before. See [validation](validation.md) for the scope of
completed tests and full-generation checks.

## Reference images

Available in 0.2.0. Follow
[Ref2VA setup](ref2va.md) to install its optional dependencies and prepare a
dedicated model bundle. Image order determines picture numbers in the prompt.

```bash
h3 generate --prompt-file prompt.txt --reference-image building.jpg --reference-image person.jpg --model-dir ~/Models/h3-apple-ref2va --duration 5 --seed 42 --output references.mp4
```

```python
result = generate(
    "Use picture 1 for the setting and picture 2 for the person.",
    reference_images=["building.jpg", "person.jpg"],
    model_dir="~/Models/h3-apple-ref2va", duration=5, seed=42,
    output="references.mp4",
)
```

The complete prompt is preserved. Each image receives its own reference segment
and aspect-preserving resize. Animated images are rejected. Supply videos using
the separate video argument below. The run record includes ordered input file hashes.

For detailed references at 768p, `--reference-resize match` retains more pixels
from large images. It preserves aspect ratio and does not enlarge small images
beyond the required 32-pixel grid rounding. It increases encoder and attention
cost and has a separate quality-validation scope; see [image sizing](ref2va.md#image-size-policy).

## Reference videos

Use the same [Ref2VA bundle](ref2va.md#installation-and-models) and optional
dependencies as image references. No additional weights are needed.

```bash
h3 generate --task ref2va --prompt-file prompt.txt --reference-video source.mp4 --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 5 --seed 42 --output edited.mp4
```

```python
result = generate(
    "Use Video 1 for the motion and Picture 1 for the subject, with outdoor ambience.",
    task="ref2va", reference_videos=["source.mp4"], reference_images=["subject.jpg"],
    reference_resize="match", model_dir="~/Models/h3-apple-ref2va",
    duration=5, seed=42, output="edited.mp4",
)
```

Repeat `--reference-video` in Video-number order. Picture numbering is separate.
Videos default to 768p output with true Dense attention and use the released H3 reference-canvas rule,
independent of the still-image resize option. Soundtracks are included as audio
references in video order; silent videos do not consume an Audio number.
See [video preparation, cost and preservation limits](ref2va-video.md).

## Reference audio

Independent audio files can accompany Ref2VA videos or reference images. They
use Dense and default to 768p. Explicit Audio numbers precede video soundtracks.

```bash
h3 generate --task ref2va --reference-image character.png --reference-audio voice.wav --prompt-file prompt.txt --model-dir ~/Models/h3-apple-ref2va --resolution 768p --reference-resize match --duration 6 --seed 42 --output dialogue.mp4
```

Use `--no-reference-video-audio` to ignore video soundtracks while keeping
explicit audio. See [numbering, Python examples and validation limits](ref2va-audio.md).

## First and last frames

Use the [FL2VA v1.2 bundle](fl2va.md) and the same optional vision dependencies
as Ref2VA. First-only and last-only requests use the FL2VA task too.

```bash
h3 generate --task fl2va --prompt-file prompt.txt --first-frame first.png --last-frame last.png --model-dir ~/Models/h3-apple-fl2va-v12 --resolution 768p --duration 5 --seed 42 --output keyframes.mp4
```

```python
result = generate(
    "A smooth continuous shot from Picture 1 to Picture 2, with natural ambience.",
    task="fl2va", first_frame="first.png", last_frame="last.png",
    model_dir="~/Models/h3-apple-fl2va-v12", resolution="768p",
    duration=5, seed=42, output="keyframes.mp4",
)
```

The recorded recipe binds the official four-step v1.2 adapter to shifts 6/3.
An older FL bundle is rejected with preparation guidance; it is never silently
relabelled or combined with the new LoRA. All three tasks report progress.

## Terminal progress

The CLI updates one line in an interactive terminal. Redirected stderr receives
plain lines, with no cursor-control codes; stdout remains valid result JSON.
Denoising percentages count completed transformer blocks across all four steps.
Encoding, decoding, muxing and validation show their stage and elapsed time;
video decoding also reports completed tiles. A denoising value of 100% means
decoding still follows. `Complete` appears after the validated MP4 is published.

```text
Denoising [##########----------]  50%  Step 2/4  |  elapsed 00:02:12
```

Python callers can keep their own callback or opt into the same display:

```python
from h3_apple.progress import ProgressBar

with ProgressBar() as progress:
    result = generate("A boat on a quiet lake.", duration=5, on_progress=progress)
```

## Output and model dimensions

| Request | Delivered MP4 | Model generation |
| --- | --- | --- |
| 768p / 15 seconds | 1366×768, 360 frames | 1376×768, 362 frames |
| 768p / 5 seconds | 1366×768, 120 frames | 1376×768, 124 frames |
| 576p / 15 seconds | 1024×576, 360 frames | 1024×576, 362 frames |
| 576p / 5 seconds | 1024×576, 120 frames | 1024×576, 124 frames |
| 768p / 15 seconds / 9:16 | 768×1366, 360 frames | 768×1376, 362 frames |
| 768p / 5 seconds / 9:16 | 768×1366, 120 frames | 768×1376, 124 frames |
| 576p / 15 seconds / 9:16 | 576×1024, 360 frames | 576×1024, 362 frames |
| 576p / 5 seconds / 9:16 | 576×1024, 120 frames | 576×1024, 124 frames |

All outputs use 24 fps and 32 kHz stereo. The fixed delivery rule center-crops
and trims to the requested frame count and audio duration, without upscaling
or interpolation. Steps, shift, VSA, and VAE settings belong to the recipe,
rather than the everyday API. Supported requests and completed hardware
validation are distinct; see [validation](validation.md).

```bash
h3 resolve --prompt-file prompt.txt --resolution 768p --duration 5 --seed 42
h3 generate --prompt-file prompt.txt --duration 5 --output runs/example.mp4
```

## Cancellation and errors

Use Ctrl-C in the CLI or catch `KeyboardInterrupt` in Python. Cancellation and
timeouts stop the worker process group and release the device lock. Failed
`.run.json` records and logs in the hidden work directory remain available at
the paths reported by the error. Inspect the failure before retrying with a
new output path. Ordinary successful runs retain an MP4 and a small run record;
diagnostic runs also retain tensors.

Invalid requests are rejected before model loading. Existing output files,
changed model assets, a busy device, unsupported hardware, and failed media
validation produce explicit errors. The API does not silently switch recipes.
Treat a prepared model directory as read-only; prepare changed weights in a
new directory.
