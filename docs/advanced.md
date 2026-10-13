# Advanced settings

Choose a quality and duration; generation resolves the remaining settings:

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --quality medium --duration 8.5
```

| Quality | Generation | Duration | Delivery, landscape |
| --- | --- | --- | --- |
| `fast` (default) | SOL, 544p + X2 decoder | 5–15 seconds | 1920×1088 |
| `medium` | VSA, native 768p | 5–15 seconds | 1366×768 |
| `high` | Dense attention, native 768p + VOSR 2× | 5 seconds | 2732×1536; also saves 1366×768 native video |

Portrait swaps the dimensions. All three accept 1–9 reference images. Fast and
medium accept **5–15 seconds at whole 24 fps frames**, including 7 and 8.5 seconds.
High is fixed at five seconds; other durations fail before model setup. Duration
defaults to five seconds for every quality. High needs 128 GiB;
medium above five seconds needs 96 GiB. Fast retains the 64 GiB minimum.
Only the 128 GiB host has been tested.

High uses BF16 full attention with the existing quantized projections and
four-step adapter, then VOSR restoration. It can retain more detail but does not
guarantee better motion, expressions or prompt adherence. Generation and
restoration have separate timeouts and measured costs.

An explicit `--quality` fixes its generation settings. Contradicting it with
`--mode`, `--attention`, `--resolution`, `--x2` or `--upscale` is an error.
Omit `--quality` to use the existing advanced combinations below. With no
advanced choices, the result is the fast configuration.

| Choice | CLI option |
| --- | --- |
| Portrait | `--aspect-ratio 9:16` |
| Duration | `--duration 7` (fast/medium: 5–15 seconds, whole frames at 24 fps; high/Dense: 5 only) |
| Generate and upscale | `--upscale`; selects native 768p + VOSR |
| Native output only | `--resolution 768p --no-x2` or `--resolution 576p --no-x2` |
| VSA generation | `--mode VSA` |
| Dense without restoration | `--mode VSA --attention dense --resolution 768p --no-x2` (5 seconds, 128 GiB) |
| Prompt file | `--prompt-file scene.txt` instead of `--prompt` |
| More references | Repeat `--image` in Picture order |
| Repeat a seed | `--seed 42` |
| Named output | `--output scene.mp4`; must be a new path |
| Machine-readable result | `--json`; automatic when stdout is redirected |

Native 768p over five seconds requires 96 GiB memory. Super-resolution requires
128 GiB. Use `h3 upscale --input video.mp4` for existing native or X2 output;
the `generate --upscale` shortcut selects native 768p for the combined workflow.

Outputs go into a fresh `runs/` directory unless you name a file. With `--quality high` or `--upscale`,
`scene.mp4` is the final video and `scene.native.mp4` is its saved input. If
restoration fails, retry with `h3 upscale --input scene.native.mp4`.

[X2 dimensions and behavior](x2.md) · [Model directories and reuse](install.md#optional-setup) ·
[Python settings and run records](api.md)

## Performance

Median time per five-second video on a 40-core M5 Max / 128 GiB, after model setup:

| Mode | Native 768p | 544p + X2 | Tradeoff in this test |
| --- | ---: | ---: | --- |
| **VSA** | 8m 49s | **4m 19s** | Less memory; fewer geometry defects |
| **SOL**, default | 6m 04s | **3m 14s** | Faster; better framing |

These are full API calls from the 0.7.0 benchmark: 12 scenes, one run per
configuration. X2 delivers **2.07× VSA / 1.91× SOL** median speedups within
matched scenes. Quality varies by scene. These times exclude VOSR restoration.
[See all 48 videos, scores and inputs](https://rhinoq.github.io/h3-apple/#results).

The fast and medium presets select the existing SOL 544p/X2 and VSA native-768p
paths respectively. The table does not measure the high workflow.

One five-second High integration clip took **31m 38s** on the same 40-core M5 Max /
128 GiB: **12m 14s** for Dense generation and **19m 24s** for optimized VOSR
(`vosr2-native-fp16-v2`). This is a single landscape clip with one reference, after
model setup; it is not a median. Both stages include loading, decoding and export.
[Run configuration and checks](evidence/v0.8.2-quality.json).

## Use with Codex

Install the [Ref2VA skill](../skills/h3-apple-ref2va-prompting/SKILL.md):

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/main/skills/h3-apple-ref2va-prompting
```

Attach images and invoke `$h3-apple-ref2va-prompting` with your brief.
The skill checks the latest stable release, handles compatible setup and uses
product defaults. Requested versions and frozen experiments stay pinned.
