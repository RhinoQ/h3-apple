# Generate locally with h3-apple

Use the public h3-apple CLI/API for rendering. This guide targets **v0.6.0**;
the [installation guide](https://github.com/RhinoQ/h3-apple/blob/v0.6.0/docs/install.md)
and [API guide](https://github.com/RhinoQ/h3-apple/blob/v0.6.0/docs/api.md) define
its supported interface. Honor a requested version; inspect that release's docs
and `--help` before adapting these commands. Do not silently upgrade an existing
installation or change the model recipe to make a command work.

## VSA and SOL

Version 0.6.0 supports `--mode VSA` (default) and `--mode SOL`, also `mode="VSA"` /
`mode="SOL"` in Python. Honor an explicitly requested mode and carry it through
`resolve`, `prepare`, `doctor`, `verify` and `generate`. Both modes use original
LightX2V. VSA needs its optional dependencies in Python 3.11 and a separate
verified model bundle. `H3_MODEL_DIR` applies to SOL, `H3_VSA_MODEL_DIR` to VSA.
Older releases such as 0.5.3 do not expose these mode flags.

## Find or install the environment

Look first at the project's documented interpreter and prior run records, then
`command -v h3` and `conda env list --json` as needed. A missing `h3` on PATH does
not prove the package is absent. Select the existing project Conda Python that
has `h3_apple`, confirm its version with `-m h3_apple --version`, and use that
absolute interpreter for every H3, pip and verification command. Do not use
system Python, Conda base, `pip --user` or an unrelated project's environment.

Before installing dependencies or downloading weights, check the host against
the selected release's requirements. v0.6.0 requires an Apple Silicon Mac with
a **40-core M5 Max**, macOS **26.2+**, and **64 GiB** unified memory; 768p beyond
5 seconds requires **96 GiB**. Read macOS and hardware information rather than
assuming that any Apple Silicon Mac is supported. Unsupported hardware is a
blocker, not a reason to bypass product checks or silently change the request.

If a compatible environment is missing, create an isolated project prefix and
install the released wheel. Choose an unused prefix if the example already
belongs to another environment. These are shell examples, not paths to assume
exist on the user's machine:

```bash
H3_ENV_PREFIX="$PWD/.local/envs/h3"
conda create --prefix "$H3_ENV_PREFIX" -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
H3_PYTHON="$H3_ENV_PREFIX/bin/python"
"$H3_PYTHON" -m pip install "h3-apple[VSA] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.6.0/h3_apple-0.6.0-py3-none-any.whl"
"$H3_PYTHON" -m h3_apple --version
```

If Conda itself is missing, install the macOS arm64 installer from the official
[Miniforge project](https://github.com/conda-forge/miniforge), verifying its
published SHA-256 first. Use an unused user-owned prefix and its absolute Conda
executable; no `sudo`, shell startup edits or `conda init` are needed. Apply the
user's download budget to dependency installation too. h3-apple is distributed
as GitHub release wheels; do not substitute an unverified PyPI package. Ordinary
generation does not need the optional face-enhancement dependencies.

## Check readiness and preparation cost

For an existing environment, set `H3_PYTHON` to the absolute Python found above.
Run `"$H3_PYTHON" -m h3_apple doctor` and inspect its JSON `ready` and `errors`,
not just whether the executable exists. It checks hardware, the environment's
FFmpeg tools/libraries, engine and model receipts. A fresh installation can be
valid while `doctor` reports missing engine/models. Repair a missing or
incompatible FFmpeg installation with Conda in this same prefix, using the
release's documented version, then recheck; reinstalling the wheel alone will
not fix a Conda media-library error.

When preparation is needed, inspect the actual plan first:

```bash
"$H3_PYTHON" -m h3_apple prepare --plan
```

Carry an existing `--model-dir` or the selected mode's model environment variable through `doctor`,
`prepare` and `generate`. The plan reports `download_bytes` and
`additional_disk_bytes`; compare the latter with free space on the destination
volume. `--plan` does not download weights or generate a video. Prefer verified
existing models and caches; `--reuse-dir` can point to known compatible sources.
Do not delete or redownload a working model installation to simplify setup.

Respect any tighter user budget. The product requires explicit consent for
downloads **over 20 GB**: show the planned transfer and disk requirement and ask
only if that transfer has not already been authorized. A request to make a video
or install the package does not by itself approve a large model download. Never
pipe `yes` into the CLI or add `--allow-large-download` to suppress this boundary.
Use that flag (or API `allow_large_download=True`) only after applicable consent.
A noninteractive run may raise `DownloadApprovalRequired`; report its plan,
obtain the missing consent, then resume. A fresh VSA preparation needs about
151 GB of downloads and 343 GB of free disk; SOL needs about 145 GB / 233 GB.
The actual mode-specific plan governs reuse.

Within the approved budget, continue automatically. `generate` prepares missing
engine/models before rendering; `prepare` is optional for advance preparation
or explicit reuse, not a substitute for the requested video. Never treat
`doctor`, `prepare` or `resolve` success as a completed generation.

## Render and deliver

Save the complete prompt in a UTF-8 file and preserve the supplied image order.
Use the requested duration, resolution, aspect ratio and seed. For omitted
settings, v0.6.0 defaults to VSA, 15 seconds, 576p, 16:9 and a recorded random seed.
Supported durations are 5–15 seconds at whole 24 fps frames; resolutions are
576p and 768p, and aspect ratios are 16:9 and 9:16. Do not quietly replace a
requested production with a shorter or lower-resolution test.

Use `resolve` to check the real inputs without loading models, then `generate`
with the same input/settings and a new output path. For example, after setting
`H3_PYTHON` and replacing these illustrative absolute paths with the actual files:

```bash
"$H3_PYTHON" -m h3_apple resolve \
  --image /absolute/path/reference.jpg --prompt-file /absolute/path/story.txt \
  --duration 5 --resolution 576p --aspect-ratio 16:9 --seed 42
"$H3_PYTHON" -m h3_apple generate \
  --image /absolute/path/reference.jpg --prompt-file /absolute/path/story.txt \
  --duration 5 --resolution 576p --aspect-ratio 16:9 --seed 42 \
  --output /absolute/path/new-video.mp4
```

Repeat `--image` for multiple references. The Python API is equivalent when an
existing workflow already uses it; invoke it with the same fixed interpreter.
Use public entry points instead of calling the native engine directly or
introducing a second renderer. Postprocessing is a separate requested operation.

Keep the process alive and monitor its progress until completion or a concrete
failure. Preserve failed run records, diagnose the cause before retrying, and
use a new output path. Do not launch an unrequested seed sweep or keep repeating
a failed command without a change that addresses its cause.

Read `video_path` and `metadata_path` from the successful result, confirm the MP4
exists and its run record says `complete`, then review the output against the
brief using [story-continuity.md](story-continuity.md). The product validates
streams, dimensions, frame count and timing; those checks do not establish
creative quality. Distinguish inspected frames, listening and unverified claims.
Return the actual absolute video path and run-record path, requested delivery
settings and relevant limitations. Show the local MP4 inline when the host
supports it. Report preparation and generation time separately when available.

## Optional X2 in a 0.7.0 installation

Check `h3 --version` before requesting this feature: the 0.6.0 release above does
not have X2. In 0.7.0, use the public `--x2` / `x2=True` option with VSA or SOL.
X2 accepts only 544p and 576p sampling: 544p produces 1920×1088 landscape or
1088×1920 portrait; 576p produces 2048×1152 or 1152×2048.
Pass `--aspect-ratio 9:16` for portrait. Use 768p without X2.
Use five seconds for the first check. Inspect task fidelity,
faces, texture and motion separately. The separate B32 reference enhancer is
not selected by this option. See the checkout's `docs/x2.md` for setup and limits.
