# H3 Ref2VA Benchmark 0.3.0

[Watch](https://rhinoq.github.io/h3-apple/) ·
[Frozen product source](https://github.com/RhinoQ/h3-apple/tree/2d8f40255b1409a19437e19987d0dd8e583bf14e)

Twelve cinematic five-second tasks, generated afresh with h3-apple 0.7.0.
Every case compares VSA and SOL at **standard 768p** and **fast 544p + X2**:
48 registered outputs, one seed per case. Prompts and unmodified references are
curated from exposed historical inputs. Historical videos and grades are excluded.
One separate portrait calibration is excluded from the score.

`catalog.json.status` identifies a registration or completed edition. A registration
contains inputs and planned requests, no videos or scores. Final scores require
all registered outputs and explicit judgments; the page never substitutes old media.

## Scores

Primary: **100 × confirmed complete visual-task passes / required slots**.
All frozen visual criteria must pass. Borderline results remain in the denominator
but are not confirmed passes. Each route has twelve cases; each mode has two
profiles of those same twelve cases, not twenty-four independent tasks.

Quality is separate: action, count, identity, geometry, detail, temporal consistency
and framing, severity 0 none / 1 minor / 2 clear / 3 severe. Report the fraction at
0–1 and every count. Speed is the complete public API call with prepared models;
memory is maximum observed process-tree physical footprint in a five-second
polling loop; short peaks may be missed. No weighted overall quality score.
Speed comparisons use the median of within-case time ratios; they are not ratios
of route medians or repeated-run confidence estimates.

Method-disclosed Agent review uses all 120 sequential frames, original keyframes
and dense intervals around critical actions. Audio is generated and decoded but
subjective sound, speech and lip sync are unscored. This is not blind review,
normal-speed audiovisual assessment or a generalization claim. No seed search,
outcome-based omission or prompt repair occurs within the frozen edition.

Runs use a 40-core M5 Max, 128 GiB, one GPU task at a time. Operating-system caches
are not flushed. Four forwards per route; equal seeds do not imply equal noise
across backends. Complete routes differ in model recipes and kernels. Output
geometry is preserved: 1366×768 / 768×1366 standard; 1920×1088 / 1088×1920 fast.
No additional resizing or enhancement is applied.

## Reproduce

Use the product's supported Conda environment, Python 3.11 and FFmpeg 8.1.2.
The site's `assets/build/` directory contains the exact wheel and native engine;
`catalog.json.primary` pins their checksums, model identities and environment.
The published product 0.6.0 is not this build.

```sh
python -m pip install "h3-apple[VSA] @ https://rhinoq.github.io/h3-apple/assets/build/h3_apple-0.7.0-py3-none-any.whl"
```

The frozen engine has no automatic URL. Populate its verified cache once:

```python
from h3_apple.assets import engine_paths
from h3_apple.downloads import download
spec, _, archive = engine_paths()
download(
    "https://rhinoq.github.io/h3-apple/assets/build/h3-engine-macos-arm64.zip",
    archive, spec["bytes"], spec["sha256"],
)
```

Prepare models separately with `h3 prepare --mode VSA --plan`, the equivalent SOL
plan and `h3 prepare-x2`. Use the corrected premerged SOL recipe. Model downloads
can exceed 20 GB and are not bundled. The frozen product documentation
retains upstream sources, component notices and preparation requirements.

Copy the complete benchmark folder, then validate and serve it locally:

```sh
python verify.py .
python -m http.server 8781 --bind 127.0.0.1
python replay.py --case cloud-palace --mode VSA --profile standard \
  --model-dir /path/to/VSA --output runs/cloud-palace-VSA.mp4
```

Replay validates inputs only until `--execute` is added. Fast execution also needs
`--x2-model-dir /path/to/x2`. Input order, duration, orientation and recorded seed
are preserved. It checks source and model identities. `--allow-different-source`
explicitly starts a new evaluation, not a claim to reproduce these pixels.

```sh
python score.py catalog.json
python package.py --catalog catalog.json --destination ../portable-benchmark
```

Scoring and normal packaging refuse incomplete or inconsistent cohorts. Replay
success is not a visual pass. Retain failures and record new judgments explicitly.

## Evidence and terms

The catalog links exact prompts, ordered references, resolved requests, run records,
criterion-level judgments, timestamps, environment, source and model identities.
Checksums bind exported bytes. Public record snapshots remove host-specific paths;
`original_sha256` identifies the unmodified local record. Original reference bytes
and prompt text are unchanged during packaging; declared prompt edits precede
registration and appear in each case's provenance.

See `ATTRIBUTION.md` for source-specific terms. Independently authored benchmark
software is Apache-2.0; that license does not relicense input images, model weights
or generated media. Reference terms with incomplete evidence remain marked unresolved.
The product source retains the MiniMax H3 license and upstream notices.
