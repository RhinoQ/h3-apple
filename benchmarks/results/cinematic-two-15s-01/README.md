# Two additional fifteen-second scene comparisons

On 2026-09-11, both The hidden key and Crystal flowers completed through Ours
and vpipe VDN: **four attempts, four successful deliveries**, without retries
or output-based selection of prompts or seeds. All passed full AV decoding
and delivery specifications. **Human audiovisual quality review remains pending**;
acceptance of the original eight videos does not extend to this round.

| Scene | Seed | Ours wait | vpipe wait | Ours wait reduction |
| --- | ---: | ---: | ---: | ---: |
| The hidden key | 15011 | 24m 52s | 29m 27s | 15.5% |
| Crystal flowers | 15012 | 25m 31s | 29m 46s | 14.3% |
| This round's two-pair mean | — | 25m 12s | 29m 36s | 14.9% |

Percentages use unrounded seconds; the aggregate is the total wait difference
divided by vpipe's total wait. This round extends inputs with the same runtime
and models. Absolute timing differences from the [original fifteen-second pairs](../native-three-02/README.md)
are not new code speedups. Each input/system ran once, Ours before vpipe.
These system observations do not establish a stable ratio, an isolated algorithmic
gain, or quality superiority. They are not pooled with five-second results.

[Watch the comparisons](../../../README.md#video-comparisons) ·
[Download native videos](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11)

## Inputs and timing

The [prompt guide](../../prompts/cinematic-two-15s/README.md) links full English
texts, official writing sources, and adaptation attribution. The
[suite](../../suites/cinematic-two-15s.json) fixes text and seeds, and the
[plan](plan.json) predates generation. The hidden key covers a person, hands,
a prop, and short dialogue. Crystal flowers covers full-body walking,
foreground occlusion, blooming, and camera movement.

Hardware was Apple M5 Max / 128 GiB / macOS 26.6.1. Common delivery is
**1366×768, 15.000 seconds, 360 frames, 24 fps, 32 kHz stereo**. Models produce
1376×768 / 362 frames, with the existing center-crop and trim rule.
Timing starts before an independent fresh process and ends after complete
AV/specification checks, including loading, generation, and muxing.
Preparation and cooling waits are excluded. Normal OS/Metal caches remain;
prompt caches start empty. All four runs used AC power with Low Power Mode off,
nominal/fair thermal readings, zero swap growth, and no stopping-condition trigger.

Both Ours runs measured 4 NFE, 200 direct sparse attention calls, and zero
fallbacks. vpipe retained its official VDN template and did not export directly
comparable structured NFE; the field remains null. Configured steps are not
substituted for measured NFE. Weights, adapters, precision, and sampling recipes
were fixed separately and differ across systems; see `weights` and `recipe`
in the results.

## Sampled-frame observations

Each video was checked at twelve evenly sampled frames including both endpoints.
This was a named, static inspection, without continuous playback or listening.
It is not blind review, audiovisual synchronization review, or full fifteen-second
quality acceptance. The sampled frames showed no whole-frame corruption.

| Video | Observation and remaining review |
| --- | --- |
| [The hidden key / Ours](diagnostics/archive-discovery-ours.jpg) | Opening the book, raising the key, and turning the head are recognizable. The camera pushes into a close-up, with multiple late orientation changes. Fingers, action continuity, dialogue, and sound require review. |
| [The hidden key / vpipe](diagnostics/archive-discovery-vpipe.jpg) | Opening the book, raising the key, and the late head turn are recognizable. Lighting is dark with a slow push-in. Shadow detail, hand/key continuity, dialogue, and sound require review. |
| [Crystal flowers / Ours](diagnostics/lunar-flower-walk-ours.jpg) | Walking, stopping, raising a hand, opening petals, and colored light are recognizable. Foreground crystals sometimes occlude the subject; the upper body remains at the lower edge near the end. Footprint continuity, gait, blooming motion, and sound require review. |
| [Crystal flowers / vpipe](diagnostics/lunar-flower-walk-vpipe.jpg) | Walking, stopping, raising a hand, opening petals, and ground light are recognizable. Foreground stems sometimes occlude the subject; the upper body remains at the lower edge near the end. Footprints, subject/petal motion, and sound require review. |

## Reproducible evidence

[results.json](results.json) records exact performance, media checks, hashes,
resources, and sampled-frame observations. [results.csv](results.csv) summarizes
the four attempts. Original failures and successes are never overwritten.
The four observation texts were translated for this edition; [provenance](../../../docs/evidence/english-edition.json)
pins the original export. Numeric and media evidence is unchanged.

- Measured source commit: `6f68563e1a7c8b76fe5187b8906dabedf25f313e`. Later commits add results/documentation; the [author map](../../../docs/evidence/github-author-map.json) locates this source in public history.
- The 43 identical installed/source runtime files have SHA256 `9151e26d4683b235a8eee422f508723a9846a9718c7ace4009a3984a1e4de9ac`.
- Model identity: `6b2716e05fd19c8d554a609bc97e46ef29c504e81f1798b02008ea003670b942`.
- vpipe commit: `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`.
- Raw evidence: `.local/comparisons/cinematic-two-15s-01/`, including each MP4, command, configuration, log, and resource record.
- Independent checks: `.local/validation/cinematic-two-15s-01/`, including preparation, fourteen related tests, completion, video-hash verification, and sampled frames.
- Local full-video index: `.local/reviews/cinematic-two-15s-01/README.md`. These local evidence paths are distinct from the public download links above.

Reproduce with the suite and a fixed installation, always writing to a new directory:

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json
```
