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
| `resolution=None` | `--resolution 768p` | `768p` or `576p`; defaults to 768p for text, 576p with reference images |
| `reference_images=None` | Repeat `--reference-image /path` | Ordered list of 1–9 still images; requires a dedicated Ref2VA bundle |
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
Those memory-budget tests cover text generation. Ref2VA has been tested with
one and four images at 576p on M5 Max / 128 GiB; other image counts, 768p reference
generation and smaller memory capacities do not yet have equivalent validation.

## Reference images

Available in the current development build (0.1.0.dev2). Follow
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
and aspect-preserving resize. Animated images and video/audio references are not
accepted by this interface. The run record includes ordered input file hashes.

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
