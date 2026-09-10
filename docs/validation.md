# Implementation and verification

Target: independently installable Ours API/CLI, reproducible model preparation, optional three-method comparison, and a product/research promotion workflow.

The preserved design is `tqlm-h3-apple/docs/h3-apple-architecture.md` at `a42bb74`.

Runtime source extraction started from adopted P091 arithmetic plus the bounded native-resolution SwiGLU fix. Historical experiments stay unchanged. New generated results must prove parity and media validity before this product is considered complete.

## Verified on 2026-09-09

- A new, private Conda environment was installed from the explicit lock. `pip check` passed. The ordinary installed wheel imports and exposes its CLI from `/tmp`, outside either repository. Importing the public API does not initialize MLX.
- 37 tests passed: request and geometry validation, local model reuse and identity checks, output ownership, process locking, timeout cleanup, complete media validation, and lazy optional diagnostics. Tests use temporary assets rather than historical model results. Evidence: `.local/validation/unit-02.log` and `.local/validation/unit-02.xml`.
- Existing model files were independently hashed and registered under `/Users/rhino/Models/h3-apple`: 33 files, 100,636,232,750 logical bytes, zero downloaded or copied model bytes. Same-filesystem hardlinks survive deletion of the old source filenames. Bundle identity: `a117c2a9ce905a6d0f3569673a43233a42eb4a579d2264b5641196be738746a1`. Evidence: `.local/validation/model-import-01.log` and the model bundle's `bundle.json`.
- An installed-wheel, free-prompt generation completed from `/tmp`: a paper boat, seed 123, 1024×576, 120 delivered frames, five seconds, 24 fps, 32 kHz stereo. End-to-end API time was 232.025 seconds. All four DiT forwards and 200 direct NAX sparse-attention calls completed without fallback; both complete media streams decoded successfully. Evidence: `.local/validation/smoke-01/plan.json`, `command.log`, `boat.run.json`, and `boat.mp4`.

Hardware: Apple M5 Max, 128 GiB, macOS 26.6.1, AC power. The smoke run started at nominal temperature, ended at fair, and showed no swap growth. This is an independent generation smoke test, not a numerical migration comparison, human quality acceptance, or a new speedup claim.

The first Conda extraction exposed a pre-existing corrupted shared package cache. That environment was rejected. Its Conda metadata and original installation logs were retained before removing the failed environment during the user's requested disk cleanup. The accepted environment uses a private cache, verified original archives, and `--copy`; it is not the environment from the failed cache attempt. Evidence: `.local/validation/environment-bootstrap.json`, `conda-install.log`, and the research repository's `docs/disk-cleanup-20260909.md`.

The optional three-method comparison script now has seven additional tests for immutable prompt hashes, exact argv substitution, preserving vpipe's official recipe, asset mutation, crop/trim delivery, timeout cleanup and failure reporting. All 44 tests pass (`.local/validation/unit-03.log`). After disk cleanup, every prepared model file was fully rehashed successfully (`.local/validation/post-cleanup-models-01.json`). No new end-to-end comparison result is implied by these tests.

## Independent conversion and migration

The full 576p/15-second bakery regression completed from `/tmp` using the
ordinary installed wheel. All 25 arrays match the adopted P091 reference in
dtype, shape and every tensor byte: conditioning, initial inputs, four denoising
steps, final latents, complete pre-clamp decoded pixels and raw stereo waveform.
The delivered 360-frame MP4 passed full media decoding. The diagnostic run took
1001.554 seconds including exports; it is not a performance benchmark. Evidence:
`.local/validation/migration-bakery-01/{plan,comparison}.json`, `bakery.run.json`
and the research repository's `scripts/verify_product_migration.py`.

The installed public `models prepare` command also reconstructed a new bundle
using fully verified local copies of all pinned native sources, with **zero model
download or cross-volume copy bytes**. All 33 original model/configuration files
match the existing bundle; the new bundle additionally includes the model license
and modification notice. Bundle v2 binds converter, source revision, quantization,
schedule and backend settings into its identity. Evidence:
`.local/validation/preparation-native-03/{plan,comparison}.json` and the conversion
receipt recorded in that bundle.

The first conversion retained 1312 identical DiT tensors but changed 302 AdaLN
cache tensors because it used the NAX-capable matrix path. This attempt is retained
as a failure to reproduce the reference. A controlled repeat used MLX's official
`MLX_METAL_GPU_ARCH=applegpu_g16s` setting in conversion only: the entire DiT and
VideoVAE files then matched their reference SHA256. This setting is now explicit
in the converter; generation clears it and uses the physical M5 architecture.
Evidence: `preparation-native-01/{file,tensor}-comparison.json` and
`preparation-native-02/comparison.json`. No second MLX installation is required.

60 installed-package tests passed after adding resume/hash/budget checks, native
parameter transforms, atomic publication, and exact final AV timing. The earlier
local HTTP fixture proxy failure and the source-mode installation test failure
were preserved; the passing result uses a normal installed package. Evidence:
`.local/validation/product-unit-04.{log,xml}`.

## Official entry preparation

FastVideo `a943220c115228ade5d57b3bab9a6a87fd600a10` is installed unchanged in a
separate Python 3.12 Conda environment; `pip check` and official pipeline import
pass. vpipe `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` builds as the official
`vpipe-cli` target with runtime Metal compilation and compatible FFmpeg headers.
Its new workspace and model registry are independent of the preserved P093
workspace. Existing Q8/VDN/Turbo assets were fully rehashed and hardlinked without
model downloads.

A fresh vpipe 576p/5-second canary completed the unchanged VDN recipe, but the
first comparison adapter rejected its 17.33 ms AAC trailing packet padding.
That failed result remains intact. The adapter now permits at most one extra AAC
packet in native media, then crops/trims and applies the unchanged strict final
check. Reprocessing the preserved native output passed full 120-frame, exactly
5-second stereo delivery. This is an adapter check, not a new end-to-end timing.
Evidence: `.local/validation/vpipe-canary-01/result.json` and
`.local/validation/vpipe-canary-delivery-02/result.json`.

The installed source also passed a native 1376×768 / 362-frame replay of one
complete 50-block forward from the preserved P093 motion case. Both full video
and audio velocity tensors were finite and byte-identical; 50 direct sparse
calls completed, using the physical `applegpu_g17s` architecture. Peak MLX memory
was 53.73 GiB. This is a native-shape numerical check, not an end-to-end timing.
Evidence: `.local/validation/native-forward-01/{plan,result}.json` and the research
script `scripts/verify_product_native_forward.py`.

A real generation cancellation after ten completed DiT blocks stopped the
worker, released the shared device lock and left no published MP4. The cancelled
run and its worker log were retained. Evidence:
`.local/validation/cancellation-01/{plan,result}.json` and `run.py`.

Actual Hugging Face HTTPS checks passed for a pinned small-file download,
resuming it after 73 bytes, and a bounded 1024-byte Range from the large VSA
adapter. The range matched the verified local payload. No complete large model
was downloaded for this test. Evidence: `.local/validation/hf-download-smoke-01/result.json`.

The final quick suite passed 62 tests (`.local/validation/product-unit-05.{log,xml}`).

## Remaining verification

The fresh six-case native 768p public comparison, full audio/video review, and
final examples/release materials. The product is not yet release-qualified.
