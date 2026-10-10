# Generate locally

Use the public h3-apple CLI/API. These examples target **0.7.0**;
[release installation](https://github.com/RhinoQ/h3-apple/blob/v0.7.0/docs/install.md)
and [API](https://github.com/RhinoQ/h3-apple/blob/v0.7.0/docs/api.md) define its contract.
Honor requested versions and settings. Check that version's docs and `--help`;
do not silently upgrade software or change model recipes.

## Environment

Find the project's interpreter in its docs and run records; use `command -v h3`
and `conda env list --json` if needed. A missing PATH entry does not prove absence.
Confirm the selected Conda Python with `-m h3_apple --version`. Use its absolute
path for H3, pip and checks. Avoid system Python, Conda base, `pip --user` and
unrelated environments.

Before installing or downloading, inspect hardware: **40-core M5 Max, macOS 26.2+,
64 GiB minimum**; native 768p beyond five seconds needs 96 GiB.
Unsupported hardware is a blocker; do not bypass guards or alter the request.

If needed, create an unused project prefix:

```bash
H3_ENV_PREFIX="$PWD/.local/envs/h3"
conda create --prefix "$H3_ENV_PREFIX" -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
H3_PYTHON="$H3_ENV_PREFIX/bin/python"
"$H3_PYTHON" -m pip install "h3-apple @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
"$H3_PYTHON" -m h3_apple --version
```

If Conda is missing, use the official [Miniforge](https://github.com/conda-forge/miniforge)
macOS arm64 installer and verify its published SHA256. Use an unused user-owned
prefix and absolute Conda path; no sudo, shell startup edits or `conda init`.
Apply the user's download budget to dependencies. Use verified GitHub wheels,
not an unverified PyPI substitute.

## Mode and models

Refreshed 0.7.0 defaults to `SOL` + 544p/X2; `VSA` is optional. Carry the requested mode through
`resolve`, `prepare`, `doctor`, `verify` and `generate`, or Python's `mode`.
Older releases such as 0.5.3 lack these flags.

Both use original LightX2V. Python 3.11 installation includes both runtimes;
VSA needs its own verified model bundle. Model variables are `H3_VSA_MODEL_DIR` for VSA and
`H3_MODEL_DIR` for SOL. Carry the selected directory through every command.

Set `H3_PYTHON` to the verified interpreter. Inspect `doctor`'s `ready` and
`errors` fields; missing models on a fresh install are expected. Repair FFmpeg
with the documented Conda version in the same prefix, not by reinstalling the wheel.

```bash
"$H3_PYTHON" -m h3_apple doctor
"$H3_PYTHON" -m h3_apple prepare --plan
```

The plan does not download weights or generate video. Compare `download_bytes`
with the budget and `additional_disk_bytes` with destination free space.
Fresh SOL + X2 needs about 150 GB / 239 GB; VSA + X2 about 156 GB / 349 GB.
Use `prepare-x2 --plan` for the separate decoder. The actual plans govern.
Reuse verified models/caches with `--reuse-dir`; do not delete working installations.

**Downloads over 20 GB need explicit consent**, subject to tighter user limits.
Show transfer and disk costs; ask only when consent is missing. A video/install
request alone does not authorize a large model download. Never pipe `yes` or use
`--allow-large-download` to bypass consent. After approval, use that flag or API
`allow_large_download=True`. If `DownloadApprovalRequired` occurs, obtain the
missing consent and resume.

Within the approved budget, proceed. `generate` prepares missing models/engine.
`prepare` is optional; readiness, preparation and input validation are not delivery.

## Render and deliver

Save the full UTF-8 prompt and preserve image order. Honor duration, resolution,
orientation and seed. Defaults are SOL, 15 seconds, 544p + X2, 16:9 and a recorded random
seed. Supported duration is 5–15 seconds in whole 24 fps frames. Do not replace a
requested production with a shorter/lower-resolution test.

Validate actual inputs, then generate to a new path:

```bash
"$H3_PYTHON" -m h3_apple resolve \
  --image /absolute/path/reference.jpg --prompt-file /absolute/path/story.txt \
  --duration 5 --aspect-ratio 16:9 --seed 42
"$H3_PYTHON" -m h3_apple generate \
  --image /absolute/path/reference.jpg --prompt-file /absolute/path/story.txt \
  --duration 5 --aspect-ratio 16:9 --seed 42 \
  --output /absolute/path/new-video.mp4
```

Repeat `--image` for multiple references. Python is equivalent when used with
the same interpreter. Use public entry points, not a second renderer or direct
native calls. Postprocessing requires its own scope.

Keep the process alive and monitor it to completion or concrete failure. Preserve
failed records, diagnose before retrying and use a new output path. Avoid
unrequested seed sweeps or unchanged retries.

Confirm the returned MP4 exists and its run record says `complete`.
[Review against the brief](story-continuity.md): stream/timing checks do not prove
creative quality. Distinguish frame inspection, listening and unverified claims.
Deliver absolute video and record paths, settings and limitations; show the MP4
inline where supported. Report setup and generation time separately.

## X2

Check the version and defaults; X2 requires 0.7.0+. Both modes use Python 3.11. SOL + X2 uses corrected premerged SOL weights and its automatically
downloaded engine, not a VSA bundle. Old quantized SOL weights need migration.

| Sampling | Landscape output | Portrait output |
| --- | --- | --- |
| 544p | 1920×1088 | 1088×1920 |
| 576p | 2048×1152 | 1152×2048 |

X2 is enabled by default; portrait uses `--aspect-ratio 9:16`.
Native output requires `--resolution 768p --no-x2` or `--resolution 576p --no-x2`
(Python: `x2=False`). For an authorized initial check, use five seconds and inspect
task fidelity, faces, texture and motion. B32 enhancement is not included.
See the checkout's `docs/x2.md`.
