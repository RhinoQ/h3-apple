# H3 Apple user guide

Choose the input that best describes the job, start with five seconds, and use
768p when small faces or fine details matter. H3 Apple generates video and
stereo audio together; a separate audio reference is optional.

This guide describes the **0.2.2 source**. Check your installation with `h3 --version`.
The [published release installation](install.md) remains 0.2.1; DARE/TIES needs
the newer source and its separately prepared Ref2VA bundle.

| I want to… | Choose / provide | Recipe selected by the product | What to expect |
| --- | --- | --- | --- |
| Generate a scene from a description | **T2VA**; text only | [Native H3 + FastH3 VSA adapter](models.md), four steps, VSA | Defaults to 768p. Describe action, camera and sound. |
| Animate a starting image or guide the ending | **FL2VA**; `--first-frame`, `--last-frame`, or both | [Native FL2VA + LightX2V FL2V v1.2 + 50 FastH3 gates](fl2va.md#model-recipe), four steps, VSA | Defaults to 768p. Anchors guide composition; the delivered endpoints are not guaranteed pixel copies. |
| Use pictures for a character, object, setting or style | **Ref2VA**; repeat `--reference-image` in prompt order | [Native Ref2VA + DARE/TIES fro0995 + 50 FastH3 gates](ref2va.md#installation-and-models), four steps, VSA; legacy LightX2V bundles remain supported | Image-only default is **576p**. Set `--resolution 768p` explicitly for small faces. |
| Use motion or edit content from an existing clip | **Ref2VA**; `--reference-video`, optionally with images | Same Ref2VA bundle and four-step weights; **Dense**, gates disabled | Defaults to 768p. Reference length and size add substantial work. Subject replacement and scene/motion preservation can still fail. |
| Guide a voice or other sound | **Ref2VA**; `--reference-audio` plus at least one image or video | Same Ref2VA bundle; four steps, **Dense** | Defaults to 768p. Audio conditions newly generated sound; it is not copied into the MP4. Voice similarity and lip sync are not guaranteed. |

The model links above contain pinned weight downloads and preparation commands.
T2VA uses FastH3, FL2VA uses LightX2V v1.2, and new Ref2VA preparation uses
DARE/TIES fro0995. The selected bundle determines which weights actually run.
They are **not interchangeable four-step LoRAs**. VSA is an attention method,
not a universal adapter-compatibility guarantee. The product selects its tested
recipe; the everyday API does not expose a Dense/VSA switch or arbitrary LoRA
loading. FL2VA v1.2 does not update Ref2VA to v1.2.

The DARE/TIES preference evidence covers image-only inputs. The earlier video
and independent-audio reviews used the LightX2V bundle; retain that bundle to
reproduce them. Support for those input types does not qualify the new adapter's
quality on them. [Adapter evidence and limitations](ref2va.md).

| Common question | Practical guidance |
| --- | --- |
| Which picture or audio number should the prompt use? | Pictures and videos each follow their own argument order: Picture 1, Video 1, etc. Explicit audio files get Audio 1, Audio 2, etc.; enabled video soundtracks follow them. State each reference's role. |
| How many references can I provide? | Up to 9 still images, 3 videos and 3 independent audio files, with **12 files total**. Each video/audio file must be 2–15 seconds. Audio requires an image or video. FL2VA anchors cannot be mixed with Ref2VA inputs. Supported counts do not imply that every combination has passed a quality review. |
| Does 768p output also mean high-resolution reference images? | No. Ref2VA defaults to `--reference-resize legacy`, about 258,048 pixels per image. For large detailed sources, opt into `--reference-resize match` to use the output model canvas's area. It costs more and does not restore missing source detail or guarantee a better result. |
| How much detail does resizing retain? | A 1920×1080 image becomes 672×384 with `legacy`, or 1376×768 with 768p `match`. A 320×192 source remains 320×192 in both. Prefer clear originals. FL2VA already prepares anchors at the model canvas; the first supplied anchor is stretched and a second is cover-cropped, so prepare matching compositions. [Sizing details](ref2va.md#image-size-policy). |
| Does lowering output resolution shrink a video reference? | No. Video preparation has its own 768-short-edge / area-capped canvas rule. Neither `--reference-resize` nor changing output to 576p changes that rule. Upscaling a small source does not recover detail. [Video preparation](ref2va-video.md#input-contract). |
| Why can a four-step job take over an hour? | Four steps is only the denoising iteration count. Longer/larger outputs, more reference frames, Dense attention, encoding and decoding all add work. Video references participate in attention on every step. Compare the complete run and its phase timings, not just the step count. |
| Are pure-image jobs also using the slower Dense route? | No. Images alone keep VSA, including with `match`. Adding a video or independent audio selects Dense. Image-only cost still rises with output size/duration and reference count/size. |
| Does VSA mean 4× faster, or Dense mean better quality? | Neither follows automatically. FL2VA/image Ref2VA use 75% nominal sparsity, but reference attention and other stages still cost time. A same-input video VSA trial failed replacement/motion checks, so video uses Dense; Dense also has recorded preservation failures. [Measured comparison](../benchmarks/results/ref2va-video-01/README.md). |
| Is H3 Apple faster than official FastH3? | There is no completed matched comparison establishing that claim. The headline speed measurements compare H3 Apple with **vpipe / VDN**, on specified prompts and hardware. [Timing scope](../README.md#measurement-and-review-scope). |
| Should I always use the newest LoRA? | Use the bundle prepared for your task and product version. FL2VA v1.2 binds its adapter to its sampling settings. Do not stack it on already fused weights or substitute it into Ref2VA. A newer adapter alone does not prove better faces, layout or audio in this runtime. |
| Can I ignore the reference video's soundtrack? | Add `--no-reference-video-audio`. Separately supplied `--reference-audio` files remain enabled. Write the intended dialogue and sound explicitly in the prompt. [Audio guide](ref2va-audio.md). |
| Is portrait output available? | Add `--aspect-ratio 9:16` (768×1366 at 768p; 576×1024 at 576p). Landscape remains the default, including for portrait inputs. Five-second 768p T2VA, two-anchor FL2VA and one-image Ref2VA runs passed full execution checks. Quality remains experimental; Dense portrait, longer portrait clips and 576p portrait generation were not included in this follow-up. [Tests and limits](validation.md#portrait-and-dense-follow-up-2026-09-18). |
| What duration and format should I request? | Start with `--duration 5`; the default is **15 seconds**. Supported output is 5–15 seconds at 24 fps, 576p or 768p, with 32 kHz stereo sound. More frames and pixels increase waiting and memory needs. |
| Is the progress bar the whole job? | All three tasks show progress. Denoising 100% is followed by decoding, muxing and validation. Wait for **Complete**. Progress is on stderr; final JSON is on stdout. `--no-progress` hides the display. |
| Is a queue managed by the generator? | Each generation has a parent process and a separate worker that holds model memory. A batch queue is a separate scheduler calling the API/CLI sequentially. The product enforces one active generation per device; run serially on one Mac. |
| Can I use a smaller Mac? | Physical testing covers **M5 Max / 128 GiB**. The release requires M5 and macOS 26.2+. The 64 GiB admission policy comes from constrained-budget text tests, not equivalent physical-machine or reference-generation validation. Check [hardware and memory](../README.md#hardware-and-memory) first. |
| How should I judge a result? | Check faces/hands, subject counts, text, reference fidelity, scene/camera preservation, motion and sound. A completed MP4, four steps or a passed numerical check does not establish visual or audio quality. [Validation scope](validation.md). |
| What should I share for reproduction? | Include the MP4, full prompt, ordered reference files/links, exact command and adjacent `.run.json`. Keep the same seed, task, model recipe and software/backend versions. Seed alone does not promise identical output across platforms. Public task reports provide full examples. |

From the product checkout, after installation and model preparation, select
its fixed Conda interpreter. The model-directory names below follow the setup
guides; replace them if you prepared your bundles elsewhere. Replace input
filenames with your local files and keep a new output path for each run.

```bash
H3_PY="$PWD/.local/envs/h3/bin/python"

# Text: no reference is required to generate sound.
"$H3_PY" -m h3_apple generate --task t2va --prompt "A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell." --model-dir ~/Models/h3-apple --resolution 768p --duration 5 --seed 42 --output bakery.mp4

# First/last frames; either anchor can also be used on its own.
"$H3_PY" -m h3_apple generate --task fl2va --prompt "A smooth continuous shot from Picture 1 to Picture 2, with natural ambience." --first-frame first.png --last-frame last.png --model-dir ~/Models/h3-apple-fl2va-v12 --resolution 768p --duration 5 --seed 42 --output keyframes.mp4

# Ordered pictures. The optional match policy retains more large-source detail.
"$H3_PY" -m h3_apple generate --task ref2va --prompt "Use Picture 1 for the setting and Picture 2 for the person. One continuous shot of the person looking around, with natural ambience." --reference-image setting.jpg --reference-image person.jpg --reference-resize match --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 5 --seed 42 --output pictures.mp4

# Video reference. Preserve/edit instructions remain quality requirements to review.
"$H3_PY" -m h3_apple generate --task ref2va --prompt "Use Video 1 for the action and camera motion. Change daylight to evening while preserving the subjects and scene layout. Natural ambience." --reference-video source.mp4 --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 5 --seed 42 --output evening.mp4

# Independent audio requires a picture or video, and selects Dense.
"$H3_PY" -m h3_apple generate --task ref2va --prompt "Use Picture 1 for the person and setting, and Audio 1 for voice timbre. The person says in English: Please stay with me. Quiet ambience, no music or subtitles." --reference-image person.jpg --reference-audio voice.wav --reference-resize match --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 6 --seed 42 --output dialogue.mp4
```

These are starting commands, not claims about generated example quality.
For a long prompt, replace `--prompt "…"` with `--prompt-file prompt.txt`.
Use `h3 resolve` with the same input options to inspect the request without
loading H3 weights. Ordinary generation retains its run record without
`--diagnostics`; diagnostic tensors require extra storage and time. The default
timeout is 7,200 seconds; set `--timeout` explicitly for an intentionally longer
job. Ctrl-C cancels the worker and retains failure information.

Observed complete runs on M5 Max / 128 GiB give useful starting points:
[one-image 576p / 5s: 5m 22s; four-image 576p / 15s: 22m 09s](../benchmarks/results/ref2va-integration-01/README.md),
[FL2VA 768p / 5s: 13m 36s](../benchmarks/results/fl2va-v12-01/README.md),
[video-reference 768p / 5s with a 2.33s source: 31m 52s](../benchmarks/results/ref2va-video-01/README.md),
and [image + audio 768p / 6s: 23m 13s](../benchmarks/results/ref2va-audio-01/README.md).
These use different inputs and recorded product versions; several include
diagnostics. They are observations, not a speed ranking, a 0.2.0 benchmark
suite or an ETA for another prompt. The linked records retain reproduction
details, failures and the separate visual/listening review boundaries.

The later [portrait and Dense checks](validation.md#portrait-and-dense-follow-up-2026-09-18)
record three complete 768p portrait runs and exact reproduction of the accepted
Dense video-reference clip on the source tree after v0.2.0.
