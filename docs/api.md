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

This generates five seconds with the fast configuration and chooses a new output
directory. Add `quality="medium"` for VSA native 768p or `quality="high"` for
Dense native 768p followed by VOSR 2× restoration. High requires 128 GiB and saves
both videos. See [requirements and terms](upscale.md).

Use `prompt_file="scene.txt"` instead of `prompt` for UTF-8 files.
Supply 1–9 still images in Picture order, with aspect ratios from 1:4 to 4:1.
EXIF orientation is applied; prompt text and image order are preserved.

## Settings

| Argument | Default | Accepted values |
| --- | --- | --- |
| `quality` | Fast configuration | `"fast"`, `"medium"`, `"high"`; omit (`None`) to customize advanced settings |
| `mode` | Automatic | `"VSA"`, `"SOL"`; without quality, defaults to SOL |
| `attention` | Automatic | `"vsa"` or `"dense"` with VSA models; Dense requires native 768p and 128 GiB |
| `duration` | `5` | 5–15 seconds, whole frames at 24 fps |
| `resolution` | Automatic | Selected by quality; otherwise `"544p"`, or `"768p"` with `upscale=True`; explicit `"576p"` also supported |
| `aspect_ratio` | `"16:9"` | `"16:9"`, `"9:16"` |
| `x2` | Automatic | On for fast, off for medium/high; without quality, on normally or off with `upscale=True`. Explicit `True` requires 544p/576p |
| `seed` | Random, recorded | Unsigned 32-bit integer |

`resolution` sets sampling size; [X2](x2.md) doubles output dimensions.
Both modes use four forwards. Equal seeds do not guarantee equal outputs across modes.

Quality and duration are independent: `quality="high", duration=7` and
`quality="medium", duration=8.5` are valid. Explicit settings that contradict a
named quality raise `ValueError` before setup. Omitted advanced settings use that
quality's values. For custom combinations, omit quality. Existing
`generate(..., upscale=True)` retains SOL native 768p + VOSR behavior.

`resolve(...)` validates generation inputs and returns a `GenerationRequest`
without loading or downloading models. It accepts the same quality, duration,
mode, attention, resolution, X2 and restoration choices as `generate(...)`.
Its width/height describe the generation stage; `upscale=True` doubles them in
the final video. `generate(...)` also accepts:

| Argument | Purpose |
| --- | --- |
| `model_dir=None` | Prepared models for the selected mode |
| `x2_model_dir=None` | X2 decoder directory; requires `x2=True` |
| `upscale=None` | Automatic from quality; otherwise off. Explicit `True` generates native video then restores with VOSR |
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

Use `generate(..., quality="high")` for Dense generation and restoration, or
`upscale("video.mp4")` for an existing native or X2 video. Both choose a fresh output
path unless you supply `output`. Restoration failures preserve the native video
and report a retry command. [Input formats, options and results](upscale.md).
