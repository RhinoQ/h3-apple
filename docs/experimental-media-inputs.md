# Experimental media inputs

This development build adds video and audio references, portrait canvases, and
first/last-frame conditioning to the Python API. These modes have narrower
validation than the stable image-reference interface. Successful decoding does
not establish motion fidelity, voice similarity, or general creative quality.

```python
from h3_apple import generate
from h3_apple.progress import ProgressBar

generate(
    "Use Picture 1 for appearance, Video 1 for motion, and Audio 1 for sound.",
    reference_images=["appearance.png"],
    reference_videos=["motion.mp4"],
    reference_audio=["sound.wav"],
    aspect_ratio="9:16",
    resolution="576p",
    duration=5,
    seed=42,
    model_dir="models/ref2va",
    output="result.mp4",
    on_progress=ProgressBar(),
)
```

Ref2VA accepts up to nine still images, three videos and three audio files, with
at most twelve files in total. Audio requires a visual reference. Images keep
their supplied order. Explicit audio is presented before video soundtracks so
that the first explicit track retains the label `Audio 1`. Video is resampled
to 24 fps, audio to 32 kHz stereo; clips are truncated at the requested model
duration. The source media is snapshotted and hashed for each run.

Use `first_frame="start.png"`, `last_frame="end.png"`, or both for FL2VA.
These inputs cannot be combined with Ref2VA inputs. The first supplied keyframe
sets the canvas by stretching; a second keyframe is resized and center-cropped
to cover the same canvas. Both are encoded by the visual conditioner and video
VAE, retained as fixed anchors throughout sampling, and excluded from decoding.

FL2VA requires a separately prepared native FL2VA bundle with the official
[LightX2V FL2VA four-step v0.1 adapter](https://huggingface.co/lightx2v/Minimax-h3-Turbo/blob/main/minimax_h3_fl2v_turbo_4step_v0.1.safetensors),
rank 128, alpha 8 and video/audio shifts 12/3. This build uses dense attention
for FL2VA. It does not apply FastH3's T2VA deltas. Its bundle can retain the fifty
VSA gate tensors for format compatibility; dense inference does not use them.
The existing T2VA and Ref2VA bundles are rejected for an FL2VA request.

Both `16:9` and `9:16` are accepted. At 576p, portrait delivery is 576×1024;
at 768p, it is 768×1366 after a centered crop from the 768×1376 model canvas.
Durations remain 5–15 seconds at 24 fps. The four-step count, isolated worker,
resource guards and progress callback apply to all modes.
