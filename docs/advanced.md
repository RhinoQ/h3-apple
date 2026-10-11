# Advanced settings

The default generates five seconds with SOL + 544p/X2. Use the
[quick start](../README.md#2-generate) before changing settings.

| Choice | CLI option |
| --- | --- |
| Portrait | `--aspect-ratio 9:16` |
| Longer clip | `--duration 15` (5–15 seconds) |
| Generate and upscale | `--upscale`; selects native 768p + VOSR |
| Native output only | `--resolution 768p --no-x2` or `--resolution 576p --no-x2` |
| VSA generation | `--mode VSA` |
| Prompt file | `--prompt-file scene.txt` instead of `--prompt` |
| More references | Repeat `--image` in Picture order |
| Repeat a seed | `--seed 42` |
| Named output | `--output scene.mp4`; must be a new path |
| Machine-readable result | `--json`; automatic when stdout is redirected |

Native 768p over five seconds requires 96 GiB memory. Super-resolution requires
128 GiB and accepts native 576p/768p; explicit X2 settings conflict with `--upscale`.

Outputs go into a fresh `runs/` directory unless you name a file. With `--upscale`,
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

## Use with Codex

Install the [Ref2VA skill](../skills/h3-apple-ref2va-prompting/SKILL.md):

```text
$skill-installer install from https://github.com/RhinoQ/h3-apple/tree/main/skills/h3-apple-ref2va-prompting
```

Attach images and invoke `$h3-apple-ref2va-prompting` with your brief.
