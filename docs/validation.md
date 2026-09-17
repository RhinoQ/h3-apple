# Implementation and validation

Independent installation, arbitrary-prompt generation, model preparation, and
the comparison script are implemented and validated as detailed below, on
**Apple M5 Max / 128 GiB / macOS 26.6.1**. Each result retains its measured
source version and scope.

The **0.1.0.dev13** candidate adds `--aspect-ratio 9:16` to all three tasks
and centers delivery crops along both axes. The default landscape request
and its numerical recipe are unchanged. Full portrait generation and visual
review remain pending; API and small-media checks alone do not establish
portrait quality or new performance results.

The previous **0.1.0.dev12** build added independent
[audio references](ref2va-audio.md) and an option to ignore video soundtracks.
Its independently installed wheel passed **286 tests**, dependency checking
and all three model-readiness checks. A complete six-second 768p image-plus-audio
run passed four-step Dense execution and exact conditioning checks against
the previous private encoder. The [audio-reference report](../benchmarks/results/ref2va-audio-01/README.md)
includes full inputs, prompt, command, timings, nonblind camera-drift observation
and separate listening limits. Numeric execution is not a voice-matching or
lip-synchronization qualification. This is a local integration, not a published
software release.

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
This is a local integration result, not a new published software release.

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
