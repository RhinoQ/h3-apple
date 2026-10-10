# Python API

Use the [H3 Conda environment](install.md).

```python
from h3_apple import generate

result = generate(
    prompt="A slow push-in on Picture 1. Soft ambient music.",
    reference_images=["reference.jpg"],
    duration=5, output="scene.mp4",
)
print(result.video_path, result.metadata_path)
```

Use `prompt_file="scene.txt"` instead of `prompt` for UTF-8 files.
Supply 1–9 still images in Picture order, with aspect ratios from 1:4 to 4:1.
EXIF orientation is applied; prompt text and image order are preserved.

## Settings

| Argument | Default | Accepted values |
| --- | --- | --- |
| `mode` | `"SOL"` | `"VSA"`, `"SOL"` |
| `duration` | `15` | 5–15 seconds, whole frames at 24 fps |
| `resolution` | `"544p"` | `"576p"`, `"768p"`; `"544p"` requires X2 |
| `aspect_ratio` | `"16:9"` | `"16:9"`, `"9:16"` |
| `x2` | `True` | `True` with 544p or 576p only |
| `seed` | Random, recorded | Unsigned 32-bit integer |

`resolution` sets sampling size; [X2](x2.md) doubles output dimensions.
Both modes use four forwards. Equal seeds do not guarantee equal outputs across modes.

`resolve(...)` validates these inputs and returns a `GenerationRequest` without
loading or downloading models. `generate(...)` also accepts:

| Argument | Purpose |
| --- | --- |
| `model_dir=None` | Prepared models for the selected mode |
| `x2_model_dir=None` | X2 decoder directory; requires `x2=True` |
| `output=None` | New MP4 path; otherwise a unique folder in `runs/` |
| `on_progress=None` | Progress callback in the caller |
| `diagnostics=False` | Keep working files |
| `timeout=7200` | Generation timeout, seconds |
| `allow_large_download=False` | Consent to downloads over 20 GB |

## First use

Missing models and runtimes are prepared automatically. The API never prompts:
`DownloadApprovalRequired` reports `download_bytes` and `additional_disk_bytes`.
Review these before retrying with `allow_large_download=True`.
Importing the package does not download anything.

## Results

`GenerationResult` contains `video_path`, `metadata_path`, `elapsed_seconds` and
`seed`. Setup time is excluded from both the timeout and `elapsed_seconds`.

Existing outputs are refused. Ctrl-C and timeout stop the worker group.
Delivery checks decode the full video and verify dimensions, frame count, timing
and stereo 32 kHz audio. Run records identify inputs, settings, models and runtime.

Audio is always generated. Describe speech, music, ambience or silence in the
prompt. Exact speech, timing, identity and continuity remain model limitations.

Native output requires `x2=False` and `resolution="576p"` or `"768p"`.
