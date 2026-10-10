# Validation

## 0.7.0 release

The [release checks](evidence/v0.7.0-release-check.json) cover normal wheel
installation, a direct 0.6.0/0.7.0 VSA profile comparison, both public entry points
and orientations, and 236 passing tests including the large-array regression.
New VSA landscape and SOL portrait outputs reproduce the frozen benchmark's
corresponding complete RGB frames and audio PCM. Only the packaged engine URL
changed from that build. See [speed and attribution](releases/0.7.0.md).

## Fresh cinematic benchmark

[Edition 0.3.0](https://rhinoq.github.io/h3-apple/) contains twelve scenes across
VSA/SOL and standard 768p/fast 544p + X2 on one frozen 0.7.0 build. Only newly
generated videos qualify. All 48 outputs have explicit criterion judgments;
historical videos and scores are excluded.

Complete visual-task success, quality severity, full API time and sampled peak
memory are separate. The site retains prompts, original references, model/source
identities, failures and replay. Review covers all sequential frames and selected
originals; subjective audio is unscored. This small, exposed regression suite has
one measurement per slot and does not establish a universal ranking.

## SOL Turbo preparation

The [controlled recipe comparison](evidence/sol-premerge-source.json) reproduced
an old duplicate-person failure with runtime Turbo and retained one person after
FP32 premerge → BF16 rounding → W8G64 preparation. Two fresh five-second cases
passed their basic subject/action gates. Small-face softness and camera movement
remain. This supports a preparation/rounding explanation for those cases, not
a universal fix or proof of a SOL attention-kernel arithmetic bug.

Installed CLI/API replays matched their selected X2 predecessors in decoded RGB
and PCM. An ordinary 576p native-decode regression also passed. The complete
portrait API pair took 158.374 s before and 169.700 s after premerge; this was an
integration check within its 1.10 ratio limit, not an acceleration claim.
The record contains all core timings, initial failures, source/model identities
and review limits.

## Historical evidence

These results retain their original recipes, inputs and qualification scope.
They are not pooled with the current comparison.

| Version | Evidence and scope |
| --- | --- |
| 0.7.0 earlier mode comparison | [Five-case frozen comparison](evidence/v0.7.0-benchmark.json); distinct source and cohort from benchmark 0.3.0 |
| 0.7.0 X2 integration | [Landscape/portrait integration](evidence/v0.7.0-x2-integration.json), including the later removed 768p + X2 route |
| 0.6.0 | [VSA performance](evidence/v0.6.0-VSA-performance.json): 1.0235× paired median, below the 1.03× incremental target; [installed CLI/API and model conversion](evidence/v0.6.0-release.json) |
| 0.5.3 | [Original-LightX2V adoption and replay](evidence/v0.5.3-release.json); non-blind frame review |
| 0.5.2 | [Generation and optional restoration checks](evidence/v0.5.2-release.json); [component provenance](evidence/v0.5.2-source-components.json) |
| 0.5.1 | [H256 decoder performance/quality](evidence/v0.5.1-performance.json): whole-generation performance gate failed; [installation](evidence/v0.5.1-release.json) |
| 0.5.0 | [Conda CLI/API integration](evidence/v0.5.0-conda.json); [native integration](evidence/v0.5.0.json) |
| 0.4.0 | [Preparation and complete Ref2VA generation](evidence/v0.4.0.json) |
| 0.3.0 and earlier | [Versioned multi-task history](https://github.com/RhinoQ/h3-apple/tree/v0.3.0/docs/validation.md) |

Synthetic numerical tests, installed-package execution, task quality, blind
review and repeated performance are distinct claims. Equal seeds alone do not
promise equal pixels across modes, builds or hardware.
