# Generate locally

Use the public h3-apple CLI/API. Handle setup for the user and use product defaults
unless the brief requires a change. Keep version and model choices out of routine
creative questions.

## Check the release

At the start of a generation or setup task, check the
[latest stable Release](https://api.github.com/repos/RhinoQ/h3-apple/releases/latest)
and the installed version. Check once per task, not before every shot.
Read `tag_name`, release notes and `assets`; exclude drafts and prereleases.
For a requested version, fetch its release by tag for matching notes and assets.
Do not infer the latest version from this skill, a branch name or an old example.

- **New work:** prefer the latest stable release. Reuse a current environment;
  apply a compatible update when needed, with a brief notice rather than a version
  selection question. Preserve existing model directories and verified caches.
- **Requested version or frozen experiment:** keep that version, environment,
  weights and recipe. Check for updates without changing the pinned run.
- **Breaking changes or material cost:** explain the concrete impact and ask only
  for the missing decision or download consent. Reuse compatible setup meanwhile.

If the release check fails, say so and use a verified compatible installation;
never call it the latest. A new installation or an explicit latest-version request
requires a verified release before proceeding.

Read `docs/install.md` and `docs/api.md` at the selected tag for requirements,
defaults and supported options. Inspect installed `--help` when adapting commands.
Select the release wheel from `assets[].browser_download_url`, download it and
verify its SHA256 against that release's `SHA256SUMS`. Do not guess a wheel URL or
substitute an unverified PyPI package. Record the release tag and installed version.

## Use one environment

Find the project's documented Conda interpreter first; use `command -v h3` and
`conda env list --json` if needed. A missing PATH entry does not prove absence.
Check the host against the selected release's requirements before installing.
Use an isolated project environment, never system Python, base or `pip --user`.
Create one only if no suitable environment exists, using the Python and FFmpeg
versions in that release's installation guide.

Set `H3_PYTHON` to its absolute interpreter and `H3_WHEEL` to the verified local
wheel. For authorized setup or a compatible update:

```bash
"$H3_PYTHON" -m pip install --upgrade "$H3_WHEEL"
"$H3_PYTHON" -m pip check
"$H3_PYTHON" -m h3_apple --version
```

Use that interpreter for every H3, pip and verification command. If Conda is
missing, use the official [Miniforge](https://github.com/conda-forge/miniforge)
macOS arm64 installer and verify its published SHA256. No sudo or shell startup
changes are needed. Do not bypass hardware or compatibility guards.

## Reuse models and check cost

Inspect `doctor`'s `ready` and `errors`, not just command success. Missing models
on a fresh install are expected. Repair FFmpeg in the same environment using the
selected release's version.

```bash
"$H3_PYTHON" -m h3_apple doctor
"$H3_PYTHON" -m h3_apple prepare --plan
```

Carry the selected mode and model directories through every command. Reuse verified
models with `--reuse-dir`; consult the selected release's installation guide for
mode-specific directories. Do not delete or redownload working models for convenience.
Include any X2 or super-resolution preparation in the complete download estimate.
Compare planned `download_bytes` with the budget and `additional_disk_bytes` with
free space. A plan does not download or render.

**Downloads over 20 GB need explicit consent**, subject to tighter user limits.
Show the combined transfer and disk costs; ask only if consent is missing.
Use `--allow-large-download` or `allow_large_download=True` only after consent;
never pipe `yes` to bypass it. Within the approved budget, continue automatically.
`generate` prepares missing components; separate `prepare` is optional.

## Generate and deliver

Save the full UTF-8 prompt and preserve image order. Honor requested duration,
orientation, resolution and seed. Otherwise use the selected release's defaults
and automatic output names:

```bash
"$H3_PYTHON" -m h3_apple generate \
  --image /absolute/path/reference.jpg --prompt-file /absolute/path/story.txt
```

Repeat `--image` for multiple references. Add only the options the brief needs.
When supported by the selected release, use `--quality fast|medium|high` for a
requested quality choice. Fast and medium support 5–15 seconds at whole 24 fps
frames, not just 5/10/15. High is fixed at five seconds and includes Dense 768p
generation and VOSR restoration; it requires 128 GiB and can take substantially longer. Consult the
release documentation for model costs and terms; do not silently replace an
explicit advanced configuration with a preset.
Use `resolve` when a separate input audit is useful. Carry its returned seed into
generation if no seed was specified, so the preflight and render agree.
Do not replace a requested production
with a shorter or lower-resolution test. Python is equivalent with the same
interpreter. Use public entry points, not direct engine calls or a second renderer.

Monitor the process through completion or a concrete failure. Preserve failed
records, diagnose before retrying and use a new output path. Avoid unrequested
seed sweeps or unchanged retries.

Confirm the returned MP4 exists and its run record says `complete`.
[Review against the brief](story-continuity.md): stream and timing checks do not
prove creative quality. Distinguish inspected frames, listening and unverified
claims. Deliver the video and record paths, actual version/settings and relevant
limitations. Show the MP4 inline where supported; separate setup and generation time.

## Optional super-resolution

Use restoration only when requested. For an existing supported video, prefer
`h3 upscale --input video.mp4`; no new generation is needed. For a new detailed
video, `h3 generate ... --quality high` selects Dense native 768p plus VOSR and
saves both versions. The existing `--upscale` path retains the SOL default.
On versions supporting qualities, validate the same choice with `resolve`.

Consult `docs/upscale.md` at the selected release for supported inputs, memory,
model downloads, measured time and noncommercial terms. Restoration preserves
audio and adds processing time; do not count it in the fast-generation headline.
