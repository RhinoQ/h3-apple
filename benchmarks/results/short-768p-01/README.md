# 768p / five-second comparison

**Four Ours/vpipe videos completed. The user subsequently canceled the official
comparison, closing this round as a two-route comparison.** Runs took place on
2026-09-11 UTC on Apple M5 Max / 128 GiB / macOS 26.6.1. Fifteen-second comparison
also retains only Ours/vpipe. Short prompts were adapted before generation.
The original JSON preserves the three-route plan and actual four-entry order.
The current [short suite](../../suites/motion-bakery-5s.json) selects Ours/vpipe
with unchanged inputs/seeds. The [scope decision](decision.json) records
cancellation without rewriting measurements.

| Entry | Motion graphics | Bakery |
| --- | ---: | ---: |
| FastH3 / Ours | 5m 54s | 5m 55s |
| vpipe / VDN | 8m 49s | 9m 01s |

Ours reduced observed waiting time by **32.96% / 34.33%**; vpipe/Ours time ratios
were 1.492 / 1.523. Each is one observation, not a repeat-measured stable ratio
or a quality win. [results.json](results.json) owns exact seconds, recipes,
runtime identities, raw-record hashes, and media checks; [CSV](results.csv)
is derived from the same data.

Common delivery is 1366×768, 120 frames, 24 fps, 5.000 seconds, 32 kHz stereo.
Each route generates 1376×768 / 124 frames using the full H3 VAE, then follows
the same crop/trim rule. Timing starts before a fresh process and ends after
complete AV decoding and specification checks. It includes model loading,
compilation, generation, muxing, and delivery cropping. Normal OS/Metal caches
remain; each prompt cache starts empty. Preparation and cooling waits are
excluded. The order was motion graphics / Ours, vpipe, then bakery / Ours,
vpipe. Completing these four before a separate official follow-up was declared
before generation; there was no output selection or rerun.

All four passed strict delivery checks, with zero swap growth, AC power, and
only nominal/fair thermal readings. Twelve sampled frames per video, including
endpoints, showed no obvious late corruption:
[motion graphics / Ours](diagnostics/motion-graphics-ours.jpg),
[motion graphics / vpipe](diagnostics/motion-graphics-vpipe.jpg),
[bakery / Ours](diagnostics/bakery-ours.jpg), and
[bakery / vpipe](diagnostics/bakery-vpipe.jpg).
This was a named, post-generation thumbnail inspection. All four later received
[human audiovisual acceptance](../../reviews/existing-eight-20260911.json),
bound to exact video hashes. Original JSON `pending` fields remain end-of-run snapshots.

[Watch the comparisons](../../../README.md#video-comparisons) ·
[Download native videos](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11)

## Actual recipes and limits

Ours used product `1e7890a41a7c2039b46fbdfcc04dbb28a09b0010`, a regular wheel,
and `ours-v1`. Native FL2VA + official VSA adapter INT8/group64 conversion and
the existing accelerated VAE were unchanged. Both runs measured 4 NFE,
200 sparse calls, and zero fallbacks. Denoising-stage MLX peaks were
33.12 / 33.11 GiB, not whole-system peaks. The [author map](../../../docs/evidence/github-author-map.json)
locates pre-publication commits in public history.

vpipe used unmodified upstream `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`,
the VDN template, FL2VA Q8, VDN stage-dmd, Turbo v4, shift 12/3, and i8_gemm.
Six configured steps produced logs with a five-step schedule and 250 denoising
blocks. Structured actual NFE and comparable internal memory peaks were not
reported and remain unknown. Identical seeds across engines do not imply
identical initial noise.

Weights, precision, steps, and algorithms differ, so the entire timing difference
cannot be attributed to one optimization. There are no held-out or repeated
samples and no conclusions about overall quality, stable speedup, or official
FastH3 speed. Immutable local evidence is in `.local/comparisons/short-768p-01/`;
`$PRODUCT` and `$MODELS` in exports are local path roles. Previous fifteen-second
results and failure evidence remain unchanged.

## Canceled official preparation: historical record

The planned official route was unmodified FastVideo
`a943220c115228ade5d57b3bab9a6a87fd600a10`, Preview v1 Dense DataFree, four steps,
INT6/group64, BF16 activations, and full FP32 VAE, without VSA, interpolation,
or reduced resolution. Official public validation used 832×480 / 124 frames;
768p required new validation. A separate official presenter short video was
planned before the two scenes. None ran before cancellation, and there is no
official successful timing.

Preparation passed 44 related regressions covering suite selection, raw AAC
rounding in both directions, target audio coverage, strict final validation,
and process boundaries. A new regular Ours wheel was installed and the official
unmodified FastVideo installation restored. The short shape has 38,752 maximum
packed rows and 1,111,097,344 SwiGLU intermediate elements. An exact-value
operator check under official MLX 0.32.2 passed. This is a pre-run check,
not a generated video.

### Weight verification

On 2026-09-10, the [official INT6 model card](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-Dense-DataFree-MLX-INT6)
described a successful output, exported size, and SHA256, but revision
`81ee7a77` contained only documentation/metadata. The actual
`mlx_h3_dit.safetensors` URL returned 404, and no other public branch or tag
was found. [preparation.json](preparation.json) preserves machine-checkable evidence.

The official conversion process could prepare INT6 from Dense DataFree
`f624f08c`. All fourteen existing text-encoder shard hashes matched, allowing
approximately 66.7 GB of reuse. The original DiT and official VAE were expected
to require about 77.3 GB of downloads. The prior request for up to 80 GB was
canceled with the official comparison; model downloading never started.
`preparation.json` retains the verification state before cancellation.

Full preparation evidence and the plan are in
`.local/validation/official-short-768p-01/`. Post-run verification and exports
for the four completed videos are in `.local/validation/short-768p-results-01/`.
