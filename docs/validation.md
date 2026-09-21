# Implementation and validation

## v0.3.0 ultrafast

Version 0.3.0 adds the optional [ultrafast preset](vpipe.md): native vpipe
INT8 GEMM + Sol-Attn + SageAttention. It supports text, first/last frames and
still-image Ref2VA using separately installed native binaries and weights.
`ours` remains the default; the unreleased native dense comparison preset is
not included. Existing `ours` video/audio-reference attention is unchanged.

The ordinary 0.3.0 wheel passed **368 regression tests** outside the checkout,
including native graph construction, full-prompt/reference order, stream
endpoints, asset checksums, acceleration fallback detection and cancellation
of native child processes. Dependency locks remain unchanged from 0.2.2.

A fresh public-CLI run with three ordered reference images and the complete
warehouse test prompt delivered **124 frames at 1024×576 / 24 fps**, with
**5.1667 seconds of 32 kHz stereo audio**, in **252.48 seconds**. Full decoding
passed. The run confirmed four denoising steps and i8/Sol/Sage settings without
a detected attention fallback. No sampled swap growth occurred. This is one
execution measurement on an M5 Max / 128 GiB / macOS 26.6.1, not a speed ranking
or a new perceptual-quality or audio-content assessment. Repeating the same
request did not produce byte-identical video or decoded audio/video streams.

The [input and execution record](evidence/ultrafast-v0.3.0.json) includes the
complete prompt, ordered public reference URLs and hashes, model/recipe and
binary identities, output checks, and a reproduction command. The tagged
[release manifest](https://github.com/RhinoQ/h3-apple/releases/download/v0.3.0/release-manifest.json)
records the final source archive, wheel, installed runtime identity, regression
and readiness checks. All packaged runtime files match the ordinary-wheel
build used for the integration run above. Earlier benchmark measurements below
retain their original versions and configurations.

Independent installation, arbitrary-prompt generation, model preparation, and
the comparison script are implemented and validated as detailed below, on
**Apple M5 Max / 128 GiB / macOS 26.6.1**. Each result retains its measured
source version and scope.

## DARE/TIES Ref2VA adoption (0.2.2)

The new Ref2VA preparation recipe uses the pinned silveroxides `fro0995`
adapter at normalized strength 1.0, four steps and shifts 12/3. Legacy
LightX2V bundles remain loadable. T2VA and FL2VA keep their existing weights
and runtime. See the [evaluation and integration record](evidence/ref2va-dareties.json).

In two known fifteen-second 768p image-reference cases, the user preferred
DARE/TIES over LightX2V v0.1. The feedback was received after adapter identities
were disclosed; these are not confirmed blind votes. Still-frame inspection
also found duplicated characters and late facial deformation in one candidate
clip. The adopted recipe preserves those observations and does not imply a
general quality improvement, independent audio/listening acceptance, or new
video/audio-reference qualification. Earlier results below retain their
original model identities.

The installed 0.2.2 ordinary wheel passed all **341 regression tests**, dependency
checks, and readiness checks for T2VA, FL2VA, legacy Ref2VA and DARE/TIES Ref2VA.
Its 53 runtime files match the evaluated candidate except for the package version;
39 native dependency binaries are unchanged. One offline public-CLI integration
run delivered 120 frames at 1024×576 and 24 fps, with five seconds of 32 kHz stereo
audio, in **239.62 seconds**. Full media decoding passed; the run recorded four
NFE, 200 VSA calls without fallback, 28.52 GiB peak denoising memory and no sampled
swap. Thermal samples were nominal or fair. This checks installation and delivery,
not new perceptual quality or a speed comparison.

The [0.2.2 release manifest](https://github.com/RhinoQ/h3-apple/releases/download/v0.2.2/release-manifest.json)
records the tagged source, artifact hashes and release-wheel checks. All runtime
files match the adopted 0.2.2 build used for the integration run above; release
packaging adds no new generation or quality result.

## v0.2.1 patch

Version 0.2.1 packages the first-use audit fixes: `doctor` checks the optional
vision dependencies for FL2VA/Ref2VA, and invalid video/audio references produce
concise CLI errors. The release also includes the installation guidance and
portrait/Dense execution evidence below. Existing model bundles and dependency
locks are unchanged from v0.2.0.

The generation implementation matches source commit `5e39dc8`, used for the
portrait/Dense follow-up; only the package version changes in the runtime.
No new H3 generation was run for patch packaging. Earlier measurements retain
their original source and package identities, and portrait quality remains
experimental. The [release manifest](https://github.com/RhinoQ/h3-apple/releases/download/v0.2.1/release-manifest.json)
records the tagged source, artifact hashes, ordinary-wheel regression checks
and model-readiness checks.

## Portrait and Dense follow-up (2026-09-18)

The ordinary wheel from source commit `5e39dc8` was run in the independent
Conda environment used for the first-use audit, outside the source checkout,
with existing prepared models and offline generation. The tests below use
the same M5 Max / 128 GiB host. Each request has a 55-minute timeout.

| Input / mode | Output | Attention | Observed CLI wait |
| --- | --- | --- | ---: |
| Text / T2VA | 768×1366, 5 seconds | VSA | 7m 46s |
| First and last frames / FL2VA | 768×1366, 5 seconds | VSA | 13m 25s |
| One image / Ref2VA, `match` resize | 768×1366, 5 seconds | VSA | 11m 16s |
| 2.33-second silent video / Ref2VA | 1366×768, 5 seconds | Dense | 32m 33s |

All four runs delivered 120 frames at 24 fps with 32 kHz stereo audio and
passed complete decoding. Each recorded four steps, valid JSON and completed
terminal progress. The three portrait runs recorded 200 VSA calls without
fallback; the video-reference run used Dense with zero sparse calls. No run
grew swap. These are individual execution checks with different inputs and
recipes, not a speed comparison. Occasional CPU inspection of completed clips
overlapped the next GPU job; this was not an isolated performance benchmark.

The Dense result is **byte-identical to the previously user-accepted clip**
in the [video-reference report](../benchmarks/results/ref2va-video-01/README.md).
Independent full RGB-frame and float-audio decoding also matches exactly, as
do the conditioning and initial-noise hashes. This preserves the earlier
nonblind acceptance for that same clip; it does not qualify arbitrary edits.

Fixed-interval frame inspection found upright, naturally framed output in
all three cases. T2VA showed a café/storefront but did not clearly establish
the requested bakery opening. FL2VA broadly followed both anchors, with a
hard cut between frames 78 and 79 rather than a demonstrated continuous camera
move. Additional inspection of frames 72–86 found no morphing transition
there. Image Ref2VA showed the referenced appearance and a smile; native-size
frames 0 and 60 had no obvious large face or hand collapse. These observations
are not a complete temporal review, blind evaluation or new human audio/visual
acceptance.

The [machine-readable record](evidence/portrait-dense-v0.2.0.json) contains
full prompts, ordered source links and hashes, reproduction commands, source
and model identities, timings, media checks, and observations. Raw logs,
MP4s and inspection frames are retained locally at the path recorded there.
The [326-test first-use regression suite](evidence/first-use-v0.2.0.json)
applies to the same source; this follow-up adds generation evidence and docs.

This follow-up did not test Dense portrait, 576p portrait, longer portrait
clips, multiple-image portrait, new independent-audio generation, or physical
64 GB hardware. It reused prepared weights rather than repeating downloads
and conversion. The v0.2.0 release archives are unchanged.

## First-use audit (2026-09-17)

The public v0.2.0 source archive and checksums were downloaded anonymously,
extracted, and installed in a new private Conda environment. Base installation,
optional reference dependencies, shell activation and imports outside the
checkout passed. Existing prepared bundles were reused; the 139 GiB weight
download and model conversion were not repeated. A pinned small-file HTTPS
download and resume passed, and the large-download guard stopped before transfer.

The initial 31 command checks exposed two issues: `doctor` reported ready for
FL2VA/Ref2VA without the optional vision packages, and corrupt video/audio
references printed tracebacks. The follow-up source commit fixes these entry checks
and clarifies CLI help. It changes no generation kernels, weights or recipes.
After installing the fixes, **31/31 command checks and 326 regression tests
passed**. Real timeout, Ctrl-C after GPU denoising began, worker exit, lock
release and output protection also passed. The cancellation run used T2VA
without PyTorch or torchvision installed. The published v0.2.0 assets remain
unchanged; these entry fixes are included in v0.2.1.

Three complete runs used the **unmodified published v0.2.0 package**:

| Input / mode | Output | Observed CLI wait |
| --- | --- | ---: |
| Text / T2VA | 768p, 5 seconds | 8m 12s |
| First and last frames / FL2VA | 768p, 5 seconds | 13m 06s |
| One image / Ref2VA | 576p, 5 seconds | 5m 11s |

Each delivered 120 frames at 24 fps with 32 kHz stereo sound, passed complete
media decoding, and recorded four steps and 200 VSA calls without fallback.
All three showed progress through completion and returned valid JSON.
Different inputs and recipes make these individual observations, not a speed
comparison or general ETA. The [audit record](evidence/first-use-v0.2.0.json)
contains exact prompts, reference extraction, commands, hashes, timings and limits.

**Execution passed; new quality acceptance is not claimed.** Fixed-interval
inspection found that FL2VA retained lettering from its last reference despite
a conflicting “no text” instruction. Ref2VA changed the reference's beige
retro-window layout into dark-background 3D shapes, missing the requested style
and composition. This audit did not repeat full portrait or Dense video/audio
generation, test physical 64 GB hardware, or perform a complete audiovisual review.

## Published v0.2.0 validation

The published **0.2.0** version is based on the **0.1.0.dev13** portrait
implementation. It adds `--aspect-ratio 9:16` to all three tasks and centers
delivery crops along both axes. The default landscape request and its
numerical recipe are unchanged. Relative to dev13, only the package version
and user documentation change; inference code, model recipes and environment
locks remain unchanged.

The independently installed dev13 wheel passed **314 tests**, including
three-task CLI/API orientation, invalid-input handling and real FFmpeg delivery
tests with vertical/horizontal padding. Small MLX unit fixtures ran on CPU;
these tests did not load H3 model weights. All three model-readiness checks
passed, and 13 existing requests resolved identically to dev12 when the new
orientation option was omitted. Only four of the 52 runtime files changed
from dev12; 74 dependency versions and 39 relevant native binaries matched.

At release, validation covered the portrait interface and delivery rather
than full model generation. The [later follow-up](#portrait-and-dense-follow-up-2026-09-18)
adds complete generation checks for three five-second 768p portrait cases.
Portrait quality remains experimental. The interface tests themselves do not
establish model execution, quality or performance. Historical results below
retain their measured versions and limitations.

The **0.1.0.dev12** build added independent
[audio references](ref2va-audio.md) and an option to ignore video soundtracks.
Its independently installed wheel passed **286 tests**, dependency checking
and all three model-readiness checks. A complete six-second 768p image-plus-audio
run passed four-step Dense execution and exact conditioning checks against
the previous private encoder. The [audio-reference report](../benchmarks/results/ref2va-audio-01/README.md)
includes full inputs, prompt, command, timings, nonblind camera-drift observation
and separate listening limits. Numeric execution is not a voice-matching or
lip-synchronization qualification. These measurements were recorded for the
local dev12 integration and are not new 0.2.0 generation measurements.

The previous **0.1.0.dev11** build added [video references](ref2va-video.md)
alongside T2VA and [FL2VA LightX2V v1.2](fl2va.md). Its 261-test installed wheel
reproduced the previously accepted five-second 768p Dense MP4 byte for byte.
The [video-reference report](../benchmarks/results/ref2va-video-01/README.md)
retains the rejected VSA trial, timings and separate Dense preservation failure.
Those results retain their original scope; the audio integration does not
requalify video editing or the unchanged T2VA/FL2VA/image-only recipes.

The earlier **0.1.0.dev2** build added ordered Ref2VA image input
and terminal progress. Its installed wheel passed **183 tests** and three
complete public-CLI regressions: one reference image, four reference images,
and text generation. All three MP4 files match their recorded baselines byte
for byte; all 60 baseline diagnostic arrays across the two Ref2VA cases are
identical. See the [integration report](../benchmarks/results/ref2va-integration-01/README.md)
for exact inputs, weights, source identity, timings and qualification limits.
These are the original local dev2 integration results, not new 0.2.0 measurements.

The published **0.1.0.dev1** preview corrects the documented `GenerationRequest`
import path and adds upstream acknowledgments. Relative to `v0.1.0.dev0`, the
only Python changes are package and CLI version strings. Generation code,
model assets, recipes, and environment locks are unchanged. This documentation
release does not add a new generation benchmark or hardware validation claim.

The [original eight videos](../benchmarks/reviews/existing-eight-20260911.json)
received human audiovisual acceptance. The sixteen videos from
[eight additional five-second scenes](../benchmarks/results/short-diverse-10-01/README.md)
and four from [two additional fifteen-second scenes](../benchmarks/results/cinematic-two-15s-01/README.md)
passed complete media validation; human quality review is pending. Those reports
retain observed visual issues. [Watch all 14 comparisons](../README.md#video-comparisons).

## Initial implementation checks

[Implementation evidence](evidence/implementation.json) records the actual plans,
results, versions, and raw-file SHA256 values. Local paths are represented by
roles. Raw logs, tensors, and failure evidence remain preserved.
The [source revision map](evidence/source-revisions.json) links recorded commit IDs
to public commits with identical Git trees.

| Check | Actual coverage and result |
| --- | --- |
| Independent installation | New private Conda environment and regular wheel; import/run from `/tmp` without a source checkout dependency; `pip check` passed |
| Fast tests | 63 passed: requests, asset identity, resume/download limits, process locks/cancellation, delivery, and comparison; temporary test data |
| Arbitrary-prompt generation | Paper boat, seed 123; 576p, 5 seconds, 120 frames, 24 fps, 32 kHz stereo; full AV decode passed |
| Full numerical migration | Bakery, 576p, 15 seconds; 25 array groups byte-identical, including conditioning, initial inputs, four denoising steps, final latent, pixels before encoding, and raw audio |
| Native-shape forward pass | One complete 50-layer forward at 1376×768 / 362 frames; complete video/audio velocities finite and byte-identical; 50 direct sparse calls |
| Independent model reconstruction | Public `models prepare` rebuilt from fully hashed local source assets; all 33 original model files identical, with licenses and modification notice added; zero model downloads |
| Real HTTPS | Pinned small-file download, resume from byte 73, and a 1024-byte Range request against the 5.34 GB adapter; matched local content |
| Real GPU cancellation | API cancellation and controller → CLI → worker cancellation passed; correct exit status, worker ended, lock released, no published MP4 |
| Distribution identity | The measured wheel, installation, and source share 43 identical runtime files; source manifests, calibration data, and licenses are packaged; weights and videos are excluded from the wheel |

Diagnostic migration and the single forward pass are correctness checks, not
complete generation speed results. Model conversion time is distinct from
download and generation time.

## Native three-route comparison

All six attempts across three entries and two full public prompts finished.
Ours and vpipe produced four 1366×768, 360-frame, 15-second, 24 fps, 32 kHz stereo
videos, passing complete decoding and dimension/duration checks. Both Ours
runs executed 4 NFE, 200 direct sparse attention calls, and zero fallbacks.
Both official FastVideo calls rejected the 362-frame request at the entry
duration check and have no successful completion time.

The subsequent [alignment fix](../benchmarks/patches/README.md) passed 32
regressions and two real CLI entry checks. Both [full follow-up attempts](../benchmarks/results/fastvideo-frame-limit-01/README.md)
generated raw videos but failed delivery-duration validation and showed damaged
late frames. They add no successful timing. Both historical rounds remain intact.

The [native-three-02 report](../benchmarks/results/native-three-02/README.md)
owns timing, source/model/environment identities, and failure boundaries.
These are single observations of each system's fixed recipe, not proof of a
new algorithmic gain, repeatable speed advantage, or overall quality superiority.

## Preserved failures and fix boundaries

The four initial five-second Ours/vpipe videos passed full AV and specification
checks. The user then canceled official FastH3 comparison and downloads. The
[short-video report](../benchmarks/results/short-768p-01/README.md) records those
outputs and 44 related passing regressions. Both current durations compare
Ours/vpipe. Raw AAC rounding tolerance still requires coverage of the requested
delivery; final checks remain strict. New results do not overwrite old failures.

- A damaged shared Conda cache caused the first environment attempt to fail. Metadata and logs remain; the accepted environment uses a private cache, verified archives, and `--copy`.
- The first conversion differed in 302 AdaLN cache tensors; the other 1312 DiT tensors matched. A controlled conversion with `applegpu_g16s` reproduced the entire reference DiT and VideoVAE hashes. Generation explicitly uses the physical M5 architecture, without a second MLX install.
- A raw vpipe short video had 17.33 ms of extra AAC tail. The delivery layer permits at most one raw AAC packet of rounding, then trims; final AV checks remain strict. Remuxing an old output proves adaptation, not a new speed result.
- The first comparison lacked FFmpeg on external processes' PATH and was stopped with evidence preserved. The controller now passes and binds the media tools, sends SIGINT first so the CLI can clean up its GPU worker, and has passed hardware cancellation checks.

Local evidence includes `.local/validation/environment-bootstrap.json` and the
`preparation-native-01/`, `preparation-native-02/`, `vpipe-canary-01/`,
`vpipe-canary-delivery-02/`, and `comparison-cancellation-02/` directories under
`.local/validation/`, plus `.local/comparisons/native-three-01/`.
These are retained local evidence locations, not public download URLs.
Completed formal results are in `.local/comparisons/native-three-02/`.

## Memory-budget validation

The [resource report](../benchmarks/results/memory-storage-01/README.md) records
subsequent complete generation and preparation under constrained total-memory
budgets. It includes the original stopped attempt, memory-policy candidates,
all completed/stopped workloads, content hashes, and measured storage.
The current installation adds a bounded GPU residency setting and checks
admitted requests by installed memory. The integrated ordinary wheel passed
88 tests and `pip check`; see the report for its complete-generation result.

The gallery timings and original migration checks above belong to their
recorded source versions. New residency-policy timings are reported separately;
old measurements are not relabeled as results of the changed runtime. The
[README](../README.md#hardware-and-memory) owns the current user-facing limits.

## Limits

Validation did not redownload the full 139 GiB model. Real network checks were
bounded as described above; conversion of all original assets was actually run.
Physical 64 GB machines, other M5 variants, other M-series generations,
unseen-content generalization, new algorithmic speed gains, and human acceptance
of the twenty additional videos remain unproven. Total-budget testing on the
128 GiB host is described separately. The README gallery contains derived
display previews; native videos remain the quality and timing reference.
