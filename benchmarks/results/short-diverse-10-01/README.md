# 768p / five seconds: ten-prompt comparison

**All sixteen new attempts delivered successfully. With the two retained pairs,
the comparison covers ten prompts and twenty videos. Ours had a shorter wait
in every pair.** The eight new pairs reduced aggregate waiting time by 35.1%;
all ten by 34.8%. These are fixed-recipe system observations. Human quality
review of the sixteen new videos is pending.

The original pairs reuse exact inputs, videos, and timings from
[short-768p-01](../short-768p-01/README.md); they are not new runs.
This extension completed on 2026-09-11 UTC, Apple M5 Max / 128 GiB / macOS 26.6.1,
with approximately 2h 19m batch wall time, without reruns or output selection.

[Prompts and sources](../../prompts/short-diverse-10/README.md) ·
[Pre-generation plan](plan.json) · [Machine results](results.json) ·
[Sixteen new entries as CSV](results.csv) ·
[Watch all comparisons](../../../README.md#video-comparisons)

## Waiting time

Each input/system has one complete delivery. Times are minutes:seconds, rounded
to the nearest second. Exact values and aggregate inputs are in `results.json`.

| Scene | Round | Ours | vpipe / VDN | Ours wait reduction |
| --- | --- | ---: | ---: | ---: |
| Motion graphics | Retained | 5:54 | 8:49 | 33.0% |
| Bakery | Retained | 5:55 | 9:01 | 34.3% |
| The old sailor | New | 5:56 | 8:57 | 33.8% |
| Rainy night bus | New | 6:02 | 9:08 | 33.9% |
| Candy keyboard | New | 5:41 | 9:11 | 38.1% |
| Canyon reveal | New | 6:06 | 9:10 | 33.4% |
| A raindrop on a rose | New | 6:06 | 9:13 | 33.8% |
| Clay campfire and fox | New | 5:49 | 9:10 | 36.6% |
| Field mouse | New | 6:07 | 9:12 | 33.6% |
| Opening an umbrella | New | 5:47 | 9:14 | 37.4% |

| Coverage | Ours mean / median | vpipe mean / median | Aggregate wait reduction | vpipe/Ours total time |
| --- | ---: | ---: | ---: | ---: |
| Eight new pairs | 5:57 / 5:59 | 9:09 / 9:10 | 35.1% | 1.540 |
| All ten pairs, including two retained | 5:56 / 5:55 | 9:07 / 9:10 | 34.8% | 1.534 |

Total waits across ten pairs were 59:24 for Ours and 91:05 for vpipe, a 31:42
difference. These sum delivery timers and exclude cooling between entries.
Reduction is `1 − sum(Ours)/sum(vpipe)`; per-pair ratios are also saved.
Different prompts are not repeated trials of the same input, so no
repeat-measurement confidence interval or stable ratio is inferred.

## Videos and quality

All sixteen new videos passed complete media decoding, dimensions, duration,
frame count/rate, channels, and sample-rate checks. Their SHA256 values match
the original run records. All eight Ours runs measured 4 NFE, 200 direct sparse
calls, and zero fallbacks. Twelve frames per video, including endpoints, showed
no obvious late corruption. This named thumbnail inspection did not include
audio listening and cannot replace full audiovisual review.

Observed prompt-adherence issues remain part of the evidence:

- **Ours / Clay campfire and fox:** the prompt asks for one camper and one fox; sampled frames show two people and two foxes.
- **vpipe / Field mouse:** the endpoint object looks rounded and egg-like, not clearly recognizable as the requested mushroom in thumbnails.
- Both candy keyboards have irregular keycap characters. Exact key-press counts, umbrella hands/mechanism, dialogue, and synchronization require full playback.

No affected video was removed, rerun, or replaced; successful delivery times
remain in the table. Speed does not establish overall quality superiority.
The [earlier acceptance](../../reviews/existing-eight-20260911.json) binds only
the old eight hashes, including the four retained short videos. All sixteen
new videos remain `pending` for human audiovisual acceptance.

| New scene | Ours sampled frames | vpipe sampled frames |
| --- | --- | --- |
| The old sailor | [View](diagnostics/sailor-dialogue-ours.jpg) | [View](diagnostics/sailor-dialogue-vpipe.jpg) |
| Rainy night bus | [View](diagnostics/night-bus-ours.jpg) | [View](diagnostics/night-bus-vpipe.jpg) |
| Candy keyboard | [View](diagnostics/candy-keyboard-ours.jpg) | [View](diagnostics/candy-keyboard-vpipe.jpg) |
| Canyon reveal | [View](diagnostics/canyon-reveal-ours.jpg) | [View](diagnostics/canyon-reveal-vpipe.jpg) |
| A raindrop on a rose | [View](diagnostics/rose-raindrop-ours.jpg) | [View](diagnostics/rose-raindrop-vpipe.jpg) |
| Clay campfire and fox | [View](diagnostics/clay-campfire-fox-ours.jpg) | [View](diagnostics/clay-campfire-fox-vpipe.jpg) |
| Field mouse | [View](diagnostics/field-mouse-ours.jpg) | [View](diagnostics/field-mouse-vpipe.jpg) |
| Opening an umbrella | [View](diagnostics/umbrella-opening-ours.jpg) | [View](diagnostics/umbrella-opening-vpipe.jpg) |

[Native MP4 downloads](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11)
are separate from the wheel. Original files remain at
`.local/comparisons/short-diverse-10-01/<case>-<method>/output.mp4`;
the retained pairs are in `.local/comparisons/short-768p-01/`.
`video_asset` and hashes identify every file. The local full-video index is
`.local/reviews/short-diverse-10-01/README.md`. Public uploads were added later
for the English gallery, without regenerating videos.

## Fixed conditions and evidence

Common delivery is 1366×768, 120 frames, 24 fps, exactly 5.000 seconds, 32 kHz
stereo. Models generate 1376×768 / 124 frames with the full H3 VAE, followed by
the same crop/trim rule. Timing includes fresh process startup, model loading,
empty-prompt cache work, generation, decoding, muxing, and full final AV checks.
Normal OS/Metal caches remain; model preparation and cooling are excluded.
Ours always preceded vpipe; order was not randomized.

Ours used product `d6398c0269c13dc1aea4d10c5bcf8ee260a1e95b`. Its 43 installed
runtime files were byte-identical to the prior short round; the regular wheel
and model bundle were unchanged. Only inputs and documentation expanded,
without a new algorithm or recipe tuning. The path remains native FL2VA +
official VSA adapter, local INT8/group64 conversion, existing NAX/VSA, and
accelerated VAE. Denoising-stage MLX peaks were 33.109–33.114 GiB, not system
peaks. The [author map](../../../docs/evidence/github-author-map.json) links
pre-publication source IDs to public history.

vpipe used unmodified upstream `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`,
its official VDN template, FL2VA Q8, VDN stage-dmd, Turbo v4, shift 12/3, and
i8_gemm. All eight logs show five-step AdaLN schedules and a final total of
250 denoising blocks. Six configured sample points include the endpoint; the
initial progress total of 300 updated to 250. Native structured `actual_nfe`
was not reported and remains null, as does a comparable internal memory peak.
Weights, steps, precision, and engines differ; identical seeds do not guarantee
identical noise. The timing difference is a complete-system comparison.

All sixteen resource records show AC power, Low Power Mode off, nominal/fair
thermal readings, and zero swap growth, without timeout or resource stops.
Raw configuration, commands, logs, resources, and videos are in
`.local/comparisons/short-diverse-10-01/`. Input freezing, completion checks,
sampled frames, and export scripts are in `.local/validation/short-diverse-10-01/`;
hashes are in the results. `$PRODUCT`, `$RESEARCH`, and `$MODELS` are local path
roles, not download URLs. Official FastH3 and its model downloads remain excluded.

## Run all ten prompts

After preparing Ours/vpipe and filling in the fixed local configuration:

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json
```

This command creates a new directory and runs all twenty entries. The recorded
extension ran only the sixteen new entries and reused the original pairs
as declared in advance.
