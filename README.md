# H3 Ref2VA Benchmark 0.3.0

[Watch the videos](https://rhinoq.github.io/h3-apple/) ·
[Frozen product source](https://github.com/RhinoQ/h3-apple/tree/2d8f40255b1409a19437e19987d0dd8e583bf14e)

**12 scenes × 4 configurations = 48 five-second videos.**
VSA and SOL, each at native 768p and fast 544p + X2, on one frozen h3-apple 0.7.0 build.
Every output is newly generated. Curated historical prompts/references are reused;
historical videos, grades and the separate portrait calibration are excluded.

## Scores

**Task success = 100 × confirmed passes / required outputs.**
Every visual criterion must pass. Borderline results remain in the denominator.
Each mode has two versions of the same 12 scenes, not 24 independent tasks.

| Measure | Definition |
| --- | --- |
| Quality | Seven dimensions; share with no/minor defects (severity 0–1) |
| Time | Full API call with prepared models; setup excluded |
| Speedup | Median of within-scene time ratios |
| Memory | Peak process-tree physical footprint, sampled every 5 s; short peaks may be missed |

Severity: **0 none · 1 minor · 2 clear · 3 severe**. Dimensions: action, count,
identity, geometry, detail, temporal consistency and framing. No weighted total.
Bars start at zero; memory shows observed min–max ranges. Time and memory stay
separate by profile.

**Review:** methods disclosed to the Agent; all 120 sequential frames, selected
originals and dense critical intervals. Audio is decoded but sound, speech and lip
sync are unscored. No blind or normal-speed audiovisual review. This exposed,
single-seed suite describes these results; it is not a general ranking.

**Conditions:** 40-core M5 Max / 128 GiB, one GPU task at a time, caches not flushed,
four forwards, one run per configuration. Recipes and kernels differ across modes;
equal seeds do not imply equal noise. No seed search, prompt repair or result omission.

Standard outputs: 1366×768 / 768×1366. Fast: 1920×1088 / 1088×1920.
No extra resizing or enhancement.

## Reproduce

Use a fresh Conda environment with Python 3.11 and FFmpeg 8.1.2.
The exact wheel/engine are in `assets/build/`; `catalog.json.primary` binds
checksums, models and environment.

```sh
conda create -n h3-benchmark -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
conda activate h3-benchmark
python -m pip install "h3-apple[VSA] @ https://rhinoq.github.io/h3-apple/assets/build/h3_apple-0.7.0-py3-none-any.whl"
```

The frozen engine has no automatic URL. Cache it once:

```python
from h3_apple.assets import engine_paths
from h3_apple.downloads import download

spec, _, archive = engine_paths()
download(
    "https://rhinoq.github.io/h3-apple/assets/build/h3-engine-macos-arm64.zip",
    archive, spec["bytes"], spec["sha256"],
)
```

Review `h3 prepare --mode VSA --plan`, the SOL equivalent and `h3 prepare-x2 --plan`,
then prepare the models. Use the premerged SOL recipe. Model downloads may exceed
20 GB and require consent; weights are not bundled.

Download the complete folder from
[`gh-pages`](https://github.com/RhinoQ/h3-apple/archive/refs/heads/gh-pages.zip),
activate the environment, then run from that folder:

```sh
python verify.py .
python replay.py --case cloud-palace --mode VSA --profile standard \
  --model-dir /path/to/VSA --output runs/cloud-palace-VSA.mp4
```

Replay validates inputs; add **`--execute`** to generate.
Fast replay also needs `--x2-model-dir /path/to/x2`.
Input order, seed, duration and orientation are preserved; source/model identities
are checked. `--allow-different-source` starts a new evaluation, not an exact replay.

To view locally: `python -m http.server 8781 --bind 127.0.0.1`.

## Score or package

```sh
python score.py catalog.json
python package.py --catalog catalog.json --destination ../portable-benchmark
```

Both reject incomplete or inconsistent scored cohorts. Registrations contain
planned inputs only; final scores require all outputs and explicit judgments.
Successful execution is not a visual pass. Retain failures and record new reviews.

## Evidence and terms

The catalog retains prompts, ordered references, requests, judgments, timestamps,
environment and build/model identities. Checksums bind exported bytes.
Public records redact host paths; `original_sha256` identifies the original record.
Packaging preserves prompt/reference bytes. Pre-registration edits are documented.

See [ATTRIBUTION.md](ATTRIBUTION.md) for input terms, including unresolved rights.
Apache-2.0 covers original benchmark code, not images, models or videos.
MiniMax terms and upstream notices still apply.
