# Official FastH3 follow-up: fastvideo-frame-limit-01

**Both full-generation attempts finished; successful deliveries: 0/2.** The
alignment patch allowed the official entry to accept the target. Both CLIs
produced native MP4 files and exited 0, but the delivery adapter rejected raw
duration checks. Subsequent sequential-frame inspection found damaged imagery
after roughly ten seconds in both videos. There is no complete-delivery timing
eligible for the speed table.

Runs took place on 2026-09-10 UTC on Apple M5 Max / 128 GiB / macOS 26.6.1,
sequentially: motion graphics, then bakery, once each on already-seen public
inputs. [results.json](results.json) is authoritative; [CSV](results.csv)
separates empty successful times from failed-attempt costs. Original records remain.

| Input | CLI raw video | Final delivery | Successful time | Failed-attempt cost |
| --- | --- | --- | ---: | ---: |
| Motion graphics / 2026 | Generated | Failed | — | 2h 4m 19s |
| Bakery / 87001 | Generated | Failed | — | 1h 49m 56s |

Failed-attempt costs run from fresh process startup to validation failure:
7458.8329740839545 and 6595.964420999866 seconds. They are not successful
delivery times and are not used for rankings or speedup ratios.

## Question and fixed configuration

The question was whether fixing only official duration alignment could complete
two fixed public 768p / fifteen-second audiovisual deliveries. The plan,
stopping conditions, and SHA are recorded in JSON. Required delivery was
**1366×768, 360 frames, fifteen seconds, 24 fps, 32 kHz stereo**. Actual model
generation was **1376×768 / 362 frames**, followed only by center-cropping
and tail trimming.

Upstream base: `a943220c115228ade5d57b3bab9a6a87fd600a10`.
Local alignment commit: `17825c79c4d839d03f3907769f6b19cc982ca5d4`.
Label: **Official FastH3 / VSA + frame-limit fix**.
See [patch and installation evidence](../../patches/README.md).
The comparison controller commit was `87f2d95`.

The official `mlx_fasth3.py` used four configured steps, VSA sparsity 0.9,
tile 64, prefix exempt, impl auto, fast/fast-spatial off, and the full FP32 H3
VideoVAE. Logs confirm **reference VSA**: each attempt had 200 attention calls,
200 sparse calls, zero fallbacks, and approximately 0.899551 actual sparsity.
The entry did not directly report NFE; original `actual_nfe` remains null.

The local native-FL2VA + official rank-64 VSA adapter conversion reused the same
effective payload as Ours. This does not establish equivalence to a downloaded
full student snapshot. No model download or parameter search occurred.
Each process and prompt cache was fresh; normal OS/Metal caches remained.
Waiting for nominal thermals and AC power was recorded separately.

## Two independent failure observations

**Raw duration boundary.** Both MP4s have 362 frames, 15.083333 seconds of video,
15.072000 seconds of AAC audio, and zero start times. Audio is approximately
**11.333 ms** shorter than the model-frame video duration but covers the target
fifteen seconds. The then-current `finish_native` validation accepted only
positive AAC tail padding, so it rejected the raw file before cropping/trimming.
No final `output.mp4` was created. Validation was not relaxed and files were
not remuxed in this round; the original failures remain failures.

**Damaged late imagery.** Both full AV bitstreams decoded with exit 0, which
does not establish valid image content. Motion graphics turned black, then
showed colored noise. Fixed-threshold blackdetect found a black interval at
9.916667–10.833333 seconds. Bakery showed widespread colored noise from roughly
ten seconds through the last frame; the same threshold found no black interval.
These are sequential raw frames 240–299, corresponding to 10.000–12.458 seconds:

![Motion graphics late-frame diagnosis](diagnostics/motion-graphics-frames-240-299.jpg)

![Bakery late-frame diagnosis](diagnostics/bakery-frames-240-299.jpg)

Motion graphics logged `invalid value encountered in cast` during pixel-to-uint8
conversion; bakery did not. Floating-point intermediates were not retained,
so the cause cannot yet be assigned to DiT, VSA, VAE, or the alignment patch.
Fixing audio validation would not repair the images. These are assistant
diagnostic observations; formal human audiovisual acceptance remains `pending`.
They are not blind review or an overall quality conclusion.

## Official phase timings: diagnosis only

| Phase, seconds | Motion graphics | Bakery |
| --- | ---: | ---: |
| Conditioning | 18.00 | 9.36 |
| Denoising | 6791.93 | 5937.42 |
| DiT forward within denoising | 6791.69 | 5937.13 |
| Video decoding | 636.06 | 638.48 |
| Audio decoding | 1.24 | 1.17 |
| Official muxing | 2.41 | 2.22 |
| Total official native generation | 7449.65 | 6588.65 |

These figures come from failed attempts' logs and exclude successful final
delivery validation. Denoising accounts for approximately 90–91% of native
generation. Denoising-stage MLX peaks were 40.11 / 39.70 GiB; video-decoding
peaks were 22.34 GiB in both. These are not process or system peaks.
Full-precision timings, VSA statistics, and phase memory values remain in JSON.

## Verification and decision

Post-run checks confirmed the clean official checkout, actual interpreter,
thirty runtime files, dependency manifest, media tools, and previously hashed
model receipts plus sizes/mtimes of 35 files. Identities matched both starts.
All raw results, configuration, logs, media, and diagnostics have SHA256 records.
Resources showed zero swap growth, nominal/fair thermals, AC power, and Low
Power Mode off, with no stop trigger. Both children exited 0; the comparison
controller exited 1. The device lock was reacquired and released.

Automatic follow-up runs stopped after this round. Ours' runtime, delivery
validation, and models remained unchanged. Attention recipes or numerical
implementations were not switched after seeing failures. A future official
comparison should first diagnose late corruption, handle raw AAC boundaries
separately, then run in a new directory.

Routine acceleration work compares stable Ours with a candidate.
Existing successful Ours/vpipe times are in [native-three-02](../native-three-02/README.md);
they were not rerun here. There is no new successful official time for a ratio.

Raw videos and large logs remain in `.local/comparisons/fastvideo-frame-limit-01/`.
The plan, full metadata, sequential diagnostics, and before/after identities
are in `.local/validation/fastvideo-frame-limit-e2e-01/`.
`$PRODUCT` and `$MODELS` are local path roles. Failed raw videos were not
published as download assets.

## Follow-up: why P084 B succeeded earlier

The maintainer pointed to successful historical P084 B videos. Its “Original MLX”
label meant the older MLX backend relative to P084 C. That entry already included
local duration handling and the mere sparse kernel; it was not an unmodified
official CLI. [Context and operator evidence](diagnostics/p084-context.json)
record the differences.

| Property | P084 B long video | This official follow-up |
| --- | --- | --- |
| Native workload | 1024×576 / 362 frames | 1376×768 / 362 frames |
| Sparse implementation | SIMD path using the local mere kernel | Official auto selected reference |
| MLX / mlx-metal | 0.32.0, original macOS 14 backend | 0.32.2, macOS 26 backend |
| Duration handling | Existing runner accepted aligned model padding, then trimmed and strictly checked delivery | Entry alignment alone was fixed; raw AAC precheck still rejected |

The first historical P091 768p long video also corrupted after roughly ten
seconds, followed by a large-tensor SwiGLU indexing fix. The same exact-value
operator was reproduced in the current official environment: the 576p shape,
64,391×28,672, was entirely correct. At the 768p shape, 113,183×28,672, sampled
row 74,899 onward produced 0 where 1024 was expected. The latter has
3,245,182,976 elements, beyond signed 32-bit indexing. Existing chunked
activation produced exactly 1024 across the complete large output. Neither
check loaded the model or regenerated a video.

This establishes a corresponding operator defect in that official environment
and a strong lead for the late corruption. Without matched intermediate tensors
or a corrected full generation, it is not established as the sole cause.
Both original failures remain. Shape-boundary checks should precede long runs;
this round's preflight omitted that check.
