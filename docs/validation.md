# Validation

## Version 0.6.0: VSA and SOL

Both modes use the original LightX2V Ref2VA Turbo four-step v0.1 recipe. SOL
retains the 0.5.3 native engine, model format and compute policy. VSA adds the
MLX implementation with W8A8 main projections, direct BF16 output, consecutive
QKV activation reuse and INT8 QK inside VSA. Mode values are uppercase; SOL is
the default. Their text encoders, attention scheduling and decoders differ, so
a shared seed does not imply equal output between modes.

The [controlled VSA evidence](evidence/v0.6.0-VSA-performance.json) includes all
12 complete runs, three full prompts, reference identities, seeds, source/model
identities, timing pairs and review scope. Three 15-second pairs against VSA
with INT8 QK alone gave **1.0235× median speedup**, with all pairs faster. This
missed the predeclared **1.03× incremental target**. Against the original
v0.2.1 VSA, the single long baseline took 2,410.856 seconds and the three
candidate runs had a 2,058.701-second median (1.1711×). That second figure uses
one baseline run and is not a three-pair estimate. These results do not compare
VSA with SOL and do not establish a universal speed or quality advantage.

The inspected VSA samples preserved the main subjects and actions, with changes
to clothing, expressions and backgrounds. The non-blind inspection found no new
severe duplication or collapse in its declared frame coverage; it did not
establish blind non-inferiority, voice quality or precise lip synchronization.
Original references and generated media are identified by hashes and are not
bundled with the package.

The [installed-package checks](evidence/v0.6.0-release.json) replayed all three
declared cases through the public interfaces on the same M5 Max / 128 GiB host:

| Mode and entry point | Delivered video | Complete wait | Replay result |
| --- | --- | ---: | --- |
| VSA CLI | 5 seconds, 1366×768, 120 frames | 623.810 s | MP4, decoded RGB and PCM equal the selected VSA predecessor |
| SOL Python API | 5 seconds, 1366×768, 120 frames | 429.195 s | MP4, decoded RGB and PCM equal the original SOL predecessor |
| VSA Python API | 15 seconds, 1366×768, 360 frames | 2,060.801 s | MP4, decoded RGB and PCM equal the selected VSA predecessor |

All runs completed four denoising forwards with stereo 32 kHz audio. VSA
executed 1,200 W8A8 projections, 800 activation packs, 400 QKV pack reuses and
200 INT8 QK / VSA calls per video, with no attention fallback. SOL retained its
executed compute routes. These single replay times verify integration and do
not establish a controlled speed comparison between modes.

Verified local VSA reuse and fresh conversion from cached original sources both
passed, with zero model-download bytes. All 70 pinned content files matched;
the long replay used the freshly converted bundle. An initial conversion used
the wrong inherited GPU architecture setting and failed the content check;
restoring the recorded Ref2VA preparation settings reproduced every file hash.
The failure and correction are retained in the evidence.

The full dependency environment passed 162 tests; a separate SOL-only
environment passed 137 with 13 optional tests skipped. A fixed restoration crop
remained pixel-identical after the shared Transformers dependency upgrade.
All 96 runtime files match between the replay wheel, final wheel, installed
package and checkout. These checks preserve the selected results without
extending their quality or hardware scope.

## Version 0.5.3

Version 0.5.3 adopts the original LightX2V Ref2VA Turbo 4-step v0.1 adapter,
pinned to revision `ec01fa4c86263832faa0bd1d6d8f36a281eaabb2`. The native engine,
base weights, four steps, video/audio shifts (12/3), adapter scale (1.0) and
compute policy are unchanged. See the [installation and replay evidence](evidence/v0.5.3-release.json).

The installed CLI and Python API each produced a complete 5-second 1366×768
video with stereo audio. Both MP4 files, decoded RGB and PCM matched their
original-LoRA comparison outputs exactly, with identical executed compute
routes and four denoising forwards. Model migration reused all base weights and
the locally cached adapter with zero download bytes; the unchanged 0.5.2
installation still loaded its original receipt. The installed core environment
passed 127 tests with 10 optional tests skipped; the environment containing face
dependencies passed all 137 tests, including 11 adapter-upgrade checks.

The adoption follows a controlled three-scene 99/bobo check using the same
0.5.2 installed runtime, references, prompts and seeds. The default dialogue
replay first reproduced the historical video and audio exactly. Only the LoRA
and its model identity changed in the three candidate runs. The six unedited
videos, complete prompts, source/weight identities and sample hashes are in the
[comparison and evidence](https://rhinoq.github.io/h3-apple/previews/99-bobo-lora-v052/).

| Scene | Observed result |
| --- | --- |
| Mandarin dialogue | Approximately equal character/scene stability; ASR matched both target lines |
| Side-tracking run | Less overlapping hand, shorts and shoe contours in the inspected motion windows; some hand blur remained |
| Bread handoff | Less ghosting during transfer and lifting; the handoff completed, with some bread/face-edge blur remaining |

These are three single-seed, five-second 768p cartoon cases on a 40-core M5 Max
with 128 GiB memory. Review was non-blind: six frames per second across each
video plus every frame in the declared action windows and full-resolution spot
checks. Subjective voice quality, precise lip sync, continuous-motion blind
review and multi-seed generalization were not evaluated. Running-clip ASR
produced a suspicious non-speech transcription in both arms; it is not evidence
of actual dialogue or subtitles. Cross-day single-run timings do not establish
a speed improvement. Adapter adoption does not guarantee the absence of blur,
unwanted text, identity drift or prompt errors.

## Version 0.5.2

Version 0.5.2 keeps the 0.5.1 native generator unchanged. Its installed CLI/API
generation checks and separate optional-restoration checks are recorded in
[the 0.5.2 release evidence](evidence/v0.5.2-release.json). The measurements
below retain their original version and scope.

## Version 0.5.1

The H256 rotated INT8 video decoder was tested on a **40-core M5 Max, 128 GiB
unified memory, macOS 26.6.1**. It keeps the original encoder, four-step DiT
recipe, adapter, attention precision and audio generation. Fixed arithmetic
selection and the executed compute routes are recorded for each generation.
There are no new mode or tuning settings.

The [performance and quality evidence](evidence/v0.5.1-performance.json) retains
inputs, source/engine identities, all paired measurements, metrics and failures.
Measurements below used frozen candidate `0.5.1.dev2`; the release uses identical
native binaries and computation policy. Release installation checks are recorded
separately from those performance results.

The [release installation evidence](evidence/v0.5.1-release.json) records a fresh
Conda Python 3.11 / FFmpeg 8.1.2 environment, a normal wheel installation and
**104 passing tests**. Public CLI and API each delivered a complete 120-frame,
1024×576 video with stereo 32 kHz audio. Decoded video/audio matched the frozen
candidate exactly. The source, wheel, sdist and installed Python/data files were
identical; all native patches were included in the sdist. Ten native tests passed
on the unchanged engine. Existing models were reused without model downloads.
These are execution checks, separate from performance and perceptual quality.

| Measurement | Result |
| --- | --- |
| Four paired fixed-latent VAE decodes | Median 1.2257× speed ratio, equivalent to 18.4% less waiting; every pair improved |
| Standalone VAE process peak | About 5.34 → 3.18 GiB |
| Three complete normal-API pairs | Candidate waiting: +6.98%, −3.45%, −4.73%; aggregate reduction 0.62% |
| Complete-generation process peak | About 59.9 → 57.7 GiB; no swap growth in the six runs |
| Three decoder quality cases | PSNR 54.73–56.99 dB; SSIM 0.99865–0.99887 |
| Full integration correctness | Conditioning, denoised video/audio latents and PCM matched the fixed-route baseline exactly |
| Repeated generation | Stable decoded video within each version; identical audio across all six runs |

The whole-generation performance target was **not met**: the first pair exceeded
the permitted 3% regression. GPU frequency varied, and the first pair's slowdown
occurred before VAE decoding. This does not establish frequency as the sole cause,
nor a consistent whole-video speed improvement. The full-version baseline was a
fixed-route 0.5.0 build; it was not the unmodified public autotuning build. The
standalone decoder comparison isolates INT8; the full candidate also includes
VAE operation fusions.

Decoder arithmetic is approximate, not bitwise lossless. Three numerical screens
and anonymous still-frame inspection passed; continuous-video human blind review
remains pending. Two validation actions share one reference subject. Results are
limited to 5-second 576p clips and do not qualify every input, long video, lower
memory configuration or other GPU. Release adoption does not change those limits.

## Version 0.5.0

Version 0.5.0 installs as a Python package in a Conda environment containing
Python and FFmpeg 8.1.2. The CLI and Python API share automatic first-run setup.
The [release evidence](evidence/v0.5.0-conda.json) records the complete input,
source and media-library identities, model verification, outputs and timing.

| Check | Result |
| --- | --- |
| Documented Conda Python + FFmpeg installation | Passed on Python 3.11 and 3.14 |
| Normal wheel installation, dependency checks and runtime preflight | Passed; Pillow is the only pip runtime dependency |
| Automatic model preparation from verified local weights | Passed; all 44 files match the pinned prepared-model manifest, zero model-download bytes |
| Public CLI generation, three reference images | Passed; 124 frames, 1024×576, 24 fps, stereo 32 kHz audio |
| Public Python API generation in Python 3.14 | Passed; 120 frames / 5 seconds, including native-frame trimming |
| Native media libraries and final processing | Passed; all seven libraries, ffmpeg and ffprobe use the running Python's Conda environment |
| Four forwards, i8 + SOL + Sage, complete media decode | Passed in both runs |
| Unit, consent, subprocess, download and media tests | 86 passed |
| Source, wheel and installed Python/data files | Identical across both complete runs and the release |

The checks ran on M5 Max with 128 GB memory and macOS 26.6.1. They use the
[complete prompt](evidence/ref2va-prompt.txt) and public references from the
0.4.0 integration case. The API requests a 5-second delivery to exercise trimming.
Both executions deliberately omit Conda tools from PATH and set an unrelated
CONDA_PREFIX; media discovery follows the actual Python interpreter.

These checks establish installation and complete execution, not a new quality
ranking, controlled speed comparison or qualification of other hardware. The
engine, weights, adapter and acceleration recipe remain pinned. The original
model download and quantization were not repeated; prior preparation evidence
is retained below. The release evidence also retains the initial synthetic-media
fixture timeout and its resolution before the passing suite.

## Version 0.4.0

Version 0.4.0 was checked on an Apple M5 Max with 128 GB unified memory and
macOS 26.6.1. The [machine-readable evidence](evidence/v0.4.0.json) includes
source identities, public reference-image URLs, the full request, output
checksums and measured media properties. The [complete prompt](evidence/ref2va-prompt.txt)
is retained without shortening.

| Check | Result |
| --- | --- |
| Fresh private Conda environment, ordinary package installation | Passed |
| Install with no existing Conda on PATH; automatic Miniforge bootstrap | Passed |
| Verified local model reuse | Passed; zero model-download bytes |
| Fresh source quantization, reusing original weights | Passed; all 44 prepared files match the accepted model SHA256 hashes |
| Unit, process-lifetime, download and real FFmpeg tests | 70 passed |
| Full three-image Ref2VA CLI generation | Passed; 254.59 seconds elapsed |
| Delivered video | 1024×576, 124 frames, 24 fps, 5.1667 seconds |
| Delivered audio | AAC stereo, 32 kHz, matching duration |
| Four actual denoising forwards; SOL and Sage enabled without fallback | Passed |
| Complete audio/video decode and validation | Passed |

The release keeps the previously tested i8 + SOL + Sage computation and
four-step Ref2VA adapter. Image sizing matches the output-area policy used
by the comparison case. This release changes installation and the product
interface; these checks do not establish a new quality ranking, a universal
speed record, exact audio-content compliance, or support for other chips.
The elapsed time is a single integration measurement, not a controlled
performance comparison. Equal seeds are inputs, not a promise of identical
GPU output bytes.

The earlier multi-method studies remain in the
[v0.3.0 source history](https://github.com/RhinoQ/h3-apple/tree/v0.3.0/docs/validation.md).
The same pinned engine, source weights and adapter identities make the
current generation path auditable without retaining the older product modes.
