# Python API

Follow the [Conda installation steps](install.md), activate the `h3` environment,
and use its Python for your script or notebook. Both the CLI and Python API use
the same installed package and Conda FFmpeg installation:

```python
from h3_apple import generate

result = generate(
    prompt="Picture 1 and Picture 2 have a picnic at sunset. Wind and birds, no dialogue.",
    reference_images=["99.jpg", "bobo.jpg"],
    output="weekend.mp4",
    mode="VSA",  # default; use "SOL" for the other mode
)
print(result.video_path)
```

`prompt_file="story.txt"` can replace `prompt`. At least one still image is
required, with at most nine; order is preserved. The image aspect ratio must
be between 1:4 and 4:1. EXIF orientation is applied before processing.

Optional delivery settings: `duration=15` (5–15 seconds in whole frames at
24 fps), `resolution="576p"` or `"768p"`, `aspect_ratio="16:9"` or `"9:16"`,
and `seed` (a 32-bit unsigned integer). `x2=True` enables the optional VSA X2
decoder and also allows `resolution="544p"`; resolution is the sampling size,
while delivered width and height are doubled. Both aspect ratios are supported.
See [exact dimensions, setup and quality limits](x2.md). Omit `seed` to choose one randomly;
it is always recorded. `mode="VSA"` (default) or `mode="SOL"` selects a fixed
implementation of the original LightX2V four-step recipe. Mode values are
uppercase. VSA requires the optional `VSA` dependencies and a VSA model bundle;
see [installation](install.md). The same seed can produce different output
between modes. A request's `mode` and `recipe` are recorded in the run metadata.

`resolve(...)` accepts these input and delivery settings and returns a
`GenerationRequest` without loading models. `generate(...)` also accepts
`model_dir`, `output`, `on_progress`, `diagnostics=False`, `timeout=7200`, and
`allow_large_download=False`, and `x2_model_dir=None` (requires `x2=True`).
The callback receives small progress dictionaries in the caller process.
Diagnostics retain intermediate media and native logs for debugging.

`generate()` automatically prepares the engine and models on first use.
It never prompts for terminal input. Downloads over 20 GB raise
`h3_apple.DownloadApprovalRequired` before downloading; its `download_bytes`
and `additional_disk_bytes` describe the plan. After reviewing the plan,
call `generate(..., allow_large_download=True)` to authorize it. Compatible
prepared models are reused without the flag. Installation, import and
`resolve()` do not download models. Preparation progress also uses the callback;
the generation timeout and `elapsed_seconds` exclude one-time preparation.

The result contains `video_path`, `metadata_path`, `elapsed_seconds` and `seed`.
Existing output files are never overwritten. Ctrl-C and timeouts stop the
entire worker process group. Successful output is decoded and checked for
frame count, dimensions, fps, two audio channels, sample rate and duration
before publication. Model, engine and input identities accompany each run. VSA records its MLX
binary identity and checks all 1,200 W8A8 projections, 800 activation packs,
400 QKV reuses and 200 INT8 QK/VSA block calls for a four-step generation.

The output always includes generated audio. Describe desired music, ambience,
dialogue or silence in the prompt. Exact sounds and synchronization remain
model capabilities, not deterministic editing controls.

## Optional enhancement of an existing video

After installing the `faces` extra and running `h3 prepare-faces`, call
`enhance_faces("video.mp4", output="enhanced.mp4")`. It uses a separate worker,
preserves input audio, skips large closeups and leaves ordinary generation unchanged.
See [the complete optional API, input limits and quality boundary](face-enhancement.md).
