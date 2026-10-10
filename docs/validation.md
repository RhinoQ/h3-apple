# Validation

## 0.7.0 release

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
| 0.5.2 | [Generation/restoration](evidence/v0.5.2-release.json); [component origins](evidence/v0.5.2-source-components.json) |
| 0.5.1 | [Decoder checks](evidence/v0.5.1-performance.json): whole-generation speed gate failed; [installation](evidence/v0.5.1-release.json) |
| 0.5.0 | [Conda CLI/API](evidence/v0.5.0-conda.json); [native integration](evidence/v0.5.0.json) |
| 0.4.0 | [Preparation and generation](evidence/v0.4.0.json) |
| ≤0.3.0 | [Versioned history](https://github.com/RhinoQ/h3-apple/tree/v0.3.0/docs/validation.md) |

Numerical correctness, execution, visual quality and performance require separate
evidence. Equal seeds do not guarantee equal pixels across modes, builds or hardware.
