# Native three-route comparison: native-three-02

All six independent attempts finished: four complete audiovisual deliveries
passed, and two official FastVideo calls rejected the requested specification.
Runs took place on 2026-09-10 UTC on **Apple M5 Max / 128 GiB / macOS 26.6.1**.
Each entry ran once on fixed public inputs. All four successful videos later
received [human audiovisual acceptance](../../reviews/existing-eight-20260911.json).
The original JSON retains `pending` as its end-of-run snapshot.

| Entry | Motion graphics | Bakery |
| --- | ---: | ---: |
| FastH3 / Ours | 36m 47s | 33m 18s |
| Official FastH3 / VSA | Entry rejected specification | Entry rejected specification |
| vpipe / VDN | 41m 15s | 39m 30s |

Timing starts before a fresh process and ends after complete final AV validation,
including loading, compilation, generation, muxing, and external delivery
conversion. Preparation and cooling waits are excluded. Normal OS and Metal
caches remain; each prompt gets a fresh process and empty prompt cache.
The fixed order was motion graphics, then bakery; within each case: Ours,
official FastH3, vpipe. Completed runs had no swap growth or resource stop.

[results.json](results.json) is the authoritative export; the table and
[CSV](results.csv) derive from it. It records source, actual environment files,
model receipts, full media checks, exact seconds, and hashes of original local
results/configuration/logs. `$PRODUCT` and `$MODELS` are local path roles.
Immutable raw evidence is in `.local/comparisons/native-three-02/`.

## Inputs and actual recipes

Delivery is **1366×768, 360 frames, 15.000 seconds, 24 fps, 32 kHz stereo**.
Models generate 1376×768 / 362 frames, followed only by center-cropping and tail
trimming. The [public suite](../../suites/motion-bakery.json) fixes full prompts
and seeds: motion graphics / 2026 and bakery / 87001. Both inputs were already
seen; identical seeds do not imply identical noise across engines.

| Entry | Actual source and recipe |
| --- | --- |
| Ours | `cc15b89156fbebf96be46d2573ab955972017ad0`, `ours-v1`; fixed native FL2VA + official VSA adapter, local INT8/group64 conversion, full VAE; both runs measured 4 NFE, 200 direct sparse calls, zero fallbacks |
| Official FastVideo | `a943220c115228ade5d57b3bab9a6a87fd600a10`, unmodified MLX CLI, VSA auto/reference, four steps, full FP32 VAE, fast/fast-spatial off; local base/adapter provenance is explicit in JSON, without claiming full-student equivalence |
| Official vpipe | `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`, unmodified official VDN template; FL2VA Q8, VDN stage-dmd, Turbo v4, six configured steps, shift 12/3, i8_gemm; actual NFE was not directly reported |

Ours' regular installation had runtime source SHA256
`b4e92640c42c85e04628308ff7929647f47866f58f3dd029d321eaf125027dab`.
The newly prepared model bundle identity was
`6b2716e05fd19c8d554a609bc97e46ef29c504e81f1798b02008ea003670b942`.
Later documentation, examples, and distribution commits do not replace this
measured version. Equivalent runtime distributions have separate identity checks.
The [source revisions](../../../docs/evidence/source-revisions.json) link recorded
commits to public source with identical Git trees.

Ours' denoising-stage MLX peaks were **54.08 / 53.66 GiB**. These are neither
process nor whole-system unified-memory peaks. vpipe did not report a comparable
internal metric, so none is inferred.

## Official entry limit and conclusions

Both unmodified official calls failed before model loading:

```text
ValueError: H3 generates 5-15 s at 24 fps; 362 frames is 15.08 s.
```

This establishes that the pinned entry rejected the required aligned shape,
not that every version, duration, or FastH3 model is unusable. Failed exit
times do not enter speed rankings. Adding local fixes requires a patched label;
changing to a shorter workload requires a separate comparison.

Complete AV decoding and strict specifications do not by themselves establish
human quality. The subsequent acceptance record applies to these exact video
hashes. [Watch the comparisons](../../../README.md#video-comparisons) or
[download native videos](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11).
Raw files and hashes remain unchanged.

These systems use different weights, adapters, precision, and recipes, with
no repeated samples or independent held-out data. The table does not establish
an operator's incremental contribution, repeatable speed superiority, a new
algorithmic gain, or overall quality superiority.
