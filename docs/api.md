# Python API

Install with `python -m pip install h3-apple`, then use the same Python:

```python
from h3_apple import generate

result = generate(
    prompt="Picture 1 and Picture 2 have a picnic at sunset. Wind and birds, no dialogue.",
    reference_images=["99.jpg", "bobo.jpg"],
    output="weekend.mp4",
)
print(result.video_path)
```

`prompt_file="story.txt"` can replace `prompt`. At least one still image is
required, with at most nine; order is preserved. The image aspect ratio must
be between 1:4 and 4:1. EXIF orientation is applied before processing.

Optional delivery settings: `duration=15` (5–15 seconds in whole frames at
24 fps), `resolution="576p"` or `"768p"`, `aspect_ratio="16:9"` or `"9:16"`,
and `seed` (a 32-bit unsigned integer). Omit `seed` to choose one randomly;
it is always recorded. There is one fixed inference recipe.

`resolve(...)` accepts these input and delivery settings and returns a
`GenerationRequest` without loading models. `generate(...)` also accepts
`model_dir`, `output`, `on_progress`, `diagnostics=False`, `timeout=7200`, and
`allow_large_download=False`.
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
before publication. Model, engine and input identities accompany each run.

The output always includes generated audio. Describe desired music, ambience,
dialogue or silence in the prompt. Exact sounds and synchronization remain
model capabilities, not deterministic editing controls.
