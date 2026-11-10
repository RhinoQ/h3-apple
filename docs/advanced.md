# Advanced settings

Choose a quality and duration; generation resolves the remaining settings:

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --quality medium --duration 8.5
```

| Quality | Generation | Duration | Delivery, landscape |
| --- | --- | --- | --- |
| `fast` (default) | 544p + X2 decoder; VSA by default, SOL optional | 5–15 seconds | 1920×1088 |
| `medium` | Native 768p; VSA by default, SOL optional | 5–15 seconds | 1366×768 |
| `high` | Pika H3 Flex, Dense attention, native 768p | 5 seconds | 1366×768 |

Portrait swaps the dimensions. All three accept 1–9 reference images. Fast and
medium accept **5–15 seconds at whole 24 fps frames**, including 7 and 8.5 seconds.
High is fixed at five seconds; other durations fail before model setup. Duration
defaults to five seconds for every quality. High needs 128 GiB;
medium above five seconds needs 96 GiB. Fast retains the 64 GiB minimum.
Only the 128 GiB host has been tested.

For Fast and Medium, choose VSA or SOL with `--mode`:

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --quality fast --mode SOL
h3 generate --image reference.jpg --prompt-file scene.txt --quality medium --mode SOL
```

Fast and Medium use the dedicated LightX2V v1.0 four-step Ref2VA adapter.
Fast keeps its integrated X2 decoder. VOSR is a separate optional restoration.
Omitting `--mode` uses VSA, including when `--quality` is omitted. Quality fixes
the sampling size and decoder; mode chooses the generation backend. Both modes
retain the same supported durations and output dimensions for each quality.

High uses six Pika H3 Flex Ref2VA forwards with BF16 Dense attention and the
quantized projections. The first High call prepares a separate Pika bundle
under the generation model root. The Pika adapter is distributed under the
MiniMax H3 Community License with the Mellis modification notice.
[Pika model card and notices](https://huggingface.co/Pika-Labs/Pika-H3-Flex/tree/ca45d99f9b1d1859ffb9dc1cd6bfaaa994257f56). Add `--upscale` to save the native file and a restored file.
Version 0.8.3 restored High automatically. For the same delivery in this version,
use `--quality high --upscale` for Pika generation with restoration. To replay
the older generator, use `--mode VSA --attention dense --resolution 768p --no-x2 --upscale`
with the released four-step model directory. Landscape changes from 1366×768 to 2732×1536
with restoration. Portrait changes from 768×1366 to 1536×2732.
[Restoration requirements and noncommercial terms](upscale.md).

An explicit `--quality` fixes attention, resolution and decoder. High accepts optional restoration. Fast and medium allow either backend;
high requires VSA models with Dense attention and rejects `--mode SOL`.
Omit `--quality` to use the existing advanced combinations below. With no
advanced choices, the result is the fast configuration.

| Choice | CLI option |
| --- | --- |
| Portrait | `--aspect-ratio 9:16` |
| Duration | `--duration 7` (fast/medium: 5–15 seconds, whole frames at 24 fps; high/Dense: 5 only) |
| Generate and upscale | `--upscale`; selects native 768p + VOSR |
| Native output only | `--resolution 768p --no-x2` or `--resolution 576p --no-x2` |
| Generation backend | `--mode VSA` (default) or `--mode SOL`; either works with fast/medium |
| Dense without restoration | `--mode VSA --attention dense --resolution 768p --no-x2` (5 seconds, 128 GiB) |
| Prompt file | `--prompt-file scene.txt` instead of `--prompt` |
| More references | Repeat `--image` in Picture order |
| Repeat a seed | `--seed 42` |
| Named output | `--output scene.mp4`; must be a new path |
| Machine-readable result | `--json`; automatic when stdout is redirected |

Native 768p over five seconds requires 96 GiB memory. Super-resolution requires
128 GiB. Use `h3 upscale --input video.mp4` for existing native or X2 output;
the `generate --upscale` shortcut selects native 768p for the combined workflow.

Outputs go into a fresh `runs/` directory unless you name a file. With `--upscale`,
`scene.mp4` is the final video and `scene.native.mp4` is its saved input. If
restoration fails, retry with `h3 upscale --input scene.native.mp4`.

[X2 dimensions and behavior](x2.md) · [Model directories and reuse](install.md#optional-setup) ·
[Python settings and run records](api.md)

## Performance

With the LightX2V v1.0 four-step weights, eight five-second scenes with three
or four reference images took a median **4m 27s on Fast** and **9m 46s on
Medium**. These full API times include generation, decoding and export on a
40-core M5 Max with 128 GiB, default VSA and prepared models.
[Per-scene times and installed-version checks](evidence/v0.9.0-qualification.json).

On the same Mac, a five-second Pika High dialogue scene with three references
took **19m 22s** through the Python API. The High CLI generated and restored a
different three-reference scene in **37m 17s**. Native generation took
**18m 50s** and optional VOSR took **18m 18s**. Both were portrait videos.
[Watch the High scenes](https://rhinoq.github.io/h3-apple/?release=0.9.0#high-dialogue).

The earlier 0.7.0 benchmark used LightX2V v0.1 on the same hardware.

| Mode | Native 768p | 544p + X2 | Tradeoff in this test |
| --- | ---: | ---: | --- |
| **VSA**, default | 8m 49s | **4m 19s** | Less memory; fewer geometry defects |
| **SOL** | 6m 04s | **3m 14s** | Faster; better framing |

These are full API calls from the 0.7.0 benchmark: 12 scenes, one run per
configuration. X2 delivers **2.07× VSA / 1.91× SOL** median speedups within
matched scenes. Quality varies by scene. These times exclude VOSR restoration.
[See all 48 videos, scores and inputs](https://rhinoq.github.io/h3-apple/#results).

Fast uses the selected backend at 544p/X2; medium uses it at native 768p.
Changing the default does not change either inference implementation. The table
does not measure the high workflow.

One five-second four-step Dense clip with VOSR took **31m 38s** on the same 40-core M5 Max /
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
