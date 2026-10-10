# Python API

Use the Python interpreter from the [H3 Conda environment](install.md).

```python
from h3_apple import generate

result = generate(
    prompt_file="scene.txt",
    reference_images=["character.jpg", "style.jpg"],
    mode="VSA",
    duration=5,
    output="scene.mp4",
)
print(result.video_path, result.metadata_path)
```

`prompt="..."` replaces `prompt_file`. Supply 1–9 still images in `Picture 1`,
`Picture 2` order. Image ratios must lie between 1:4 and 4:1; EXIF orientation is
applied. Prompt text and image order are preserved.

| Setting | Default | Accepted values |
| --- | --- | --- |
| `mode` | `"VSA"` | `"VSA"`, `"SOL"` |
| `duration` | `15` | 5–15 seconds, whole frames at 24 fps |
| `resolution` | `"576p"` | `"576p"`, `"768p"`; `"544p"` requires X2 |
| `aspect_ratio` | `"16:9"` | `"16:9"`, `"9:16"` |
| `x2` | `False` | `True` only with 544p or 576p |
| `seed` | Random, recorded | Unsigned 32-bit integer |

`resolution` is the sampling size. X2 doubles delivered dimensions in either
mode; see [dimensions, dependencies and limits](x2.md). Both modes use four
forwards, but equal seeds do not imply equal output.

`resolve(...)` accepts these settings and returns a `GenerationRequest` without
loading models. `generate(...)` additionally accepts:

| Argument | Purpose |
| --- | --- |
| `model_dir=None` | Selected mode's prepared model directory |
| `x2_model_dir=None` | Separate decoder directory; requires `x2=True` |
| `output=None` | New MP4 path; otherwise a unique folder under `runs/` |
| `on_progress=None` | Callback receiving progress dictionaries in the caller |
| `diagnostics=False` | Retain working files for inspection |
| `timeout=7200` | Generation timeout in seconds |
| `allow_large_download=False` | Explicit consent for downloads above 20 GB |

First use prepares missing models and the selected mode's runtime automatically;
see [installation requirements](install.md#before-you-start).
The API never prompts. `DownloadApprovalRequired` exposes `download_bytes`
and `additional_disk_bytes`; review them before authorizing the download.
Import and `resolve()` do not download. Preparation time is excluded from
generation's timeout and `elapsed_seconds`.

The result contains `video_path`, `metadata_path`, `elapsed_seconds` and `seed`.
Existing outputs are refused. Ctrl-C and timeout terminate the worker group.
Before delivery, the complete media is decoded and checked for dimensions,
frame count, fps, duration and stereo 32 kHz audio. Run records bind the request,
inputs, model, source, backend and executed compute policy.

Audio is always generated. Describe dialogue, music, ambience or silence in
the prompt; exact sound, timing, identity and continuity remain model limitations.

## Optional enhancement of an existing video

After installing `[faces]` and preparing its models:

```python
from h3_apple import enhance_faces
result = enhance_faces("scene.mp4", output="scene-enhanced.mp4")
```

This separate worker preserves source audio and skips large closeups.
See [the enhancement contract](face-enhancement.md).
