# Validation

## 0.8.1

[X2 restoration checks](evidence/v0.8.1-x2-vosr.json): **278 tests passed**, with
one optional large-array test skipped. The installed wheel restores all eight
supported input sizes. Default X2 uses a 24-frame landscape clip and an eight-frame
portrait clip; the larger 576p X2 sizes use two-frame resized fixtures. Four native
sizes reproduce their two frozen restored PNGs exactly. Audio and silence are preserved.
Final packaging matches the source tree exactly and repeats the X2 CLI pixel/audio
check. The record distinguishes the geometry-test and clean delivery builds.

These checks establish compatibility and native regression, not complete X2 motion
quality or a new speed ranking. The separate
[five-second workflow check](evidence/v0.8.1-workflow.json) uses native 768p.

## 0.8.0

[Release checks](evidence/v0.8.0-release.json): **241 tests passed** in a clean
Conda installation, including GPU, large-array, dependency and cancellation checks.
Full five-second SOL landscape/portrait and VSA runs match the frozen 0.7.0
outputs in every decoded RGB frame and PCM sample.

The installed VOSR CLI reproduced the complete **120-frame N8 MP4 byte for byte**,
including audio. Python checks cover the N6 excerpt, portrait and
both native 576p orientations. These short geometry checks use two frames each;
they do not qualify general scene quality or long-clip performance.

[Restoration measurements](evidence/v0.8.0-vosr.json) retain the separate N8
FP32 comparison, N6 historical reference and complete human playback review.
The final dependency-guard correction leaves restoration code and data unchanged.

## Refreshed 0.7.0

[Refresh checks](evidence/v0.7.0-refresh.json): **219 passing tests**, including the
large-array regression; a fresh Conda install without extras; default SOL + X2
through landscape CLI and portrait Python calls; explicit VSA + X2. All three
five-second outputs match the original configurations in complete decoded RGB
and audio PCM.

## Initial 0.7.0 release

[Release checks](evidence/v0.7.0-release-check.json): wheel installation, model reuse,
CLI/API generation in both orientations, and **236 passing tests**, including the
large-array regression. Fresh VSA landscape and SOL portrait runs matched the
benchmark's decoded RGB and audio PCM. Packaging changed the engine URL, not its bytes.

[Release notes](releases/0.7.0.md) contain speed measurements and source credits.

## Fresh cinematic benchmark

[Benchmark 0.3.0](https://rhinoq.github.io/h3-apple/) compares **12 scenes × 4 configurations**:
VSA/SOL at native 768p and 544p + X2. All 48 videos were generated on one frozen
0.7.0 build. Prompts, references, settings, failures and replay files are public.

Task success, quality, full API time and sampled memory are scored separately.
Agent review covers every sequential frame and selected originals, with methods
disclosed. Audio quality is unscored. One seed and one run per configuration make
this an exposed regression suite, not a general ranking.

## SOL Turbo preparation

[Controlled comparison](evidence/sol-premerge-source.json): runtime Turbo reproduced
a duplicate-person failure; **FP32 merge → BF16 rounding → W8G64** retained one
person. Two fresh five-second portrait/landscape cases passed their subject/action
criteria. Small-face softness and camera errors remained.

Installed CLI/API replays matched the selected X2 outputs in RGB and PCM; ordinary
576p decoding also passed. The portrait API pair took **158.374 s → 169.700 s**,
within its 1.10 ratio limit. This was a correctness check, not a speedup.

The evidence supports a preparation/rounding explanation for these cases.
It does not establish a universal fix or a SOL attention-kernel defect.

## Historical evidence

These records retain their original builds and review scope; they are excluded
from the current benchmark.

| Version | Evidence |
| --- | --- |
| 0.7.0 | [Earlier five-case comparison](evidence/v0.7.0-benchmark.json); [X2 integration](evidence/v0.7.0-x2-integration.json), including the removed 768p + X2 route |
| 0.6.0 | [Performance](evidence/v0.6.0-VSA-performance.json): 1.0235× paired median, below the 1.03× target; [CLI/API and conversion](evidence/v0.6.0-release.json) |
| 0.5.3 | [LightX2V adoption and replay](evidence/v0.5.3-release.json); non-blind frame review |
| 0.5.2 | [Archived generation/restoration checks](https://github.com/RhinoQ/h3-apple/blob/v0.5.2/docs/validation.md) |
| 0.5.1 | [Decoder checks](evidence/v0.5.1-performance.json): whole-generation speed gate failed; [installation](evidence/v0.5.1-release.json) |
| 0.5.0 | [Conda CLI/API](evidence/v0.5.0-conda.json); [native integration](evidence/v0.5.0.json) |
| 0.4.0 | [Preparation and generation](evidence/v0.4.0.json) |
| ≤0.3.0 | [Versioned history](https://github.com/RhinoQ/h3-apple/tree/v0.3.0/docs/validation.md) |

Numerical correctness, execution, visual quality and performance require separate
evidence. Equal seeds do not guarantee equal pixels across modes, builds or hardware.
