# Python API

Use the [H3 Conda environment](install.md).

```python
from h3_apple import generate

result = generate(
    prompt="A slow push-in on Picture 1. Soft ambient music.",
    reference_images=["reference.jpg"],
)
print(result.video_path, result.metadata_path)
```

This generates five seconds and chooses a new output directory. Add `upscale=True`
to generate native 768p and restore it at twice the dimensions. See
[requirements and terms](upscale.md).

Use `prompt_file="scene.txt"` instead of `prompt` for UTF-8 files.
Supply 1–9 still images in Picture order, with aspect ratios from 1:4 to 4:1.
EXIF orientation is applied; prompt text and image order are preserved.

## Settings

| Argument | Default | Accepted values |
| --- | --- | --- |
| `mode` | `"SOL"` | `"VSA"`, `"SOL"` |
| `duration` | `5` | 5–15 seconds, whole frames at 24 fps |
| `resolution` | Automatic | `"544p"` normally, `"768p"` with `upscale=True`; explicit `"576p"` also supported |
| `aspect_ratio` | `"16:9"` | `"16:9"`, `"9:16"` |
| `x2` | Automatic | On normally; off with `upscale=True`. Explicit `True` requires 544p/576p and conflicts with super-resolution |
| `seed` | Random, recorded | Unsigned 32-bit integer |

`resolution` sets sampling size; [X2](x2.md) doubles output dimensions.
Both modes use four forwards. Equal seeds do not guarantee equal outputs across modes.

`resolve(...)` validates generation inputs and returns a `GenerationRequest`
without loading or downloading models. Its defaults are explicitly 544p and X2;
the restoration workflow is selected through `generate(...)`, which also accepts:

| Argument | Purpose |
| --- | --- |
| `model_dir=None` | Prepared models for the selected mode |
| `x2_model_dir=None` | X2 decoder directory; requires `x2=True` |
| `upscale=False` | Generate native video, then restore it with VOSR; saves both videos |
| `upscale_model_dir=None` | Restoration model directory; requires `upscale=True` |
| `upscale_timeout=14400` | Restoration timeout, seconds; separate from generation |
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
`seed`, plus `native_video_path` when super-resolution is enabled (`None` otherwise).
Setup time is excluded from both the timeout and `elapsed_seconds`. With
super-resolution, elapsed time sums the two stages; each retains its own timer
and run record. The final record links the native video and its generation record.

Existing outputs are refused. Ctrl-C and timeout stop the worker group.
Delivery checks decode the full video and verify dimensions, frame count, timing
and stereo 32 kHz audio. Run records identify inputs, settings, models and runtime.

Audio is always generated. Describe speech, music, ambience or silence in the
prompt. Exact speech, timing, identity and continuity remain model limitations.

Native output requires `x2=False` and `resolution="576p"` or `"768p"`.

## Super-resolution

Use `generate(..., upscale=True)` for the complete workflow, or
`upscale("video.mp4")` for an existing native or X2 video. Both choose a fresh output
path unless you supply `output`. Restoration failures preserve the native video
and report a retry command. [Input formats, options and results](upscale.md).
