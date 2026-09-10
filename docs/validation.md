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

## Remaining verification

Fresh-machine download and conversion, numerical migration comparisons, actual cancellation during generation, the six-case public comparison, complete installation/API documentation, licenses and release materials. The product is not yet release-qualified.
