# Installation and your first video

Check the [hardware and memory requirements](../README.md#hardware-and-memory)
before installing. The README distinguishes physical-machine validation,
constrained total-memory budgets and the requests admitted at each capacity.
Review the [disk-space budget](../README.md#disk-space) for setup and everyday
generation. Run on AC power.

## Conda environment

Install ARM64 [Miniforge](https://github.com/conda-forge/miniforge), or use an
existing ARM64 Conda installation. Install the
[v0.1.0.dev1 pre-release](https://github.com/RhinoQ/h3-apple/releases/tag/v0.1.0.dev1):

```bash
git clone --branch v0.1.0.dev1 --single-branch https://github.com/RhinoQ/h3-apple.git
cd h3-apple
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 --version
```

Alternatively, download `h3-apple-0.1.0.dev1-source.zip` from the release,
extract it, and run `./install.sh` from the extracted directory. The archive
contains the installer, environment locks, documentation, and examples.
`SHA256SUMS` verifies the attached archives, wheel, and release manifest:

```bash
shasum -a 256 -c SHA256SUMS
```

Run that check in the directory containing all four release assets. Model
weights are downloaded separately by `h3 models prepare`. The wheel alone
does not set up the pinned Conda environment or download models.

The installer uses the readable [environment definition](../environments/environment.yml)
and exact [osx-arm64 lock](../environments/conda-osx-arm64.lock). It creates a
private Conda cache and environment, with Python 3.11.15, MLX 0.32.0, FFmpeg 8.1.2,
and locked Python dependencies. It installs a regular wheel without changing
system Python or user site-packages. Text generation does not require PyTorch.
The current development build adds [Ref2VA images, videos and audio references](ref2va.md),
[FL2VA LightX2V v1.2](fl2va.md), and terminal progress; these are not included
in the pinned v0.1.0.dev1 release. From the development
checkout, `./install.sh --ref2va` also installs the pinned PyTorch/torchvision
vision dependencies. Rerunning `./install.sh` installs the current checkout.

Scripts and schedulers should use the fixed interpreter:

```bash
"$PWD/.local/envs/h3/bin/python" -m h3_apple --version
```

MLX publishes different platform wheels under the same version number. The
installer selects the macOS 26 backend, and `doctor` checks the loaded libraries.
Matching `pip freeze` output alone does not verify the backend.

## Models and offline generation

See [model preparation](models.md) for downloads, reuse, storage requirements,
and recovery. Once the model is ready:

```bash
h3 doctor
h3 generate --prompt "A paper boat drifts across a quiet pond. Soft water sounds and birdsong." --duration 5 --output boat.mp4
```

The example requests five seconds and fits the experimental 64 GiB entry.
Omitting duration/resolution flags requests 768p / 15 seconds and requires at
least 96 GiB. For a smaller first check:

```bash
h3 generate --prompt "A paper boat drifts across a quiet pond. Soft water sounds and birdsong." --resolution 576p --duration 5 --seed 123 --output boat-smoke.mp4
```

If models are missing, `doctor` exits nonzero and points to `h3 models prepare`.
Generation enables Hugging Face and Transformers offline mode; it does not
download missing components during a run.

## Recovery

- **Conda not found:** install Conda, or set `CONDA_EXE` to its absolute executable path.
- **Missing models:** run model preparation; register existing files with `--reuse-dir`.
- **Backend mismatch:** rerun `./install.sh` instead of replacing a single library manually.
- **Device busy:** wait for the current H3 job. The shared device lock defaults to `~/.cache/h3-apple/device.lock`.
- **Resource stop:** inspect the `.run.json` and logs, free disk or memory, or allow cooling, then retry with a new output path.
- **Interrupted installation or download:** rerun the command. Retain error logs; corrupt files are not accepted as complete assets.

`H3_MODEL_DIR` changes the default model directory. `H3_DEVICE_LOCK` sets the
lock path shared by cooperating jobs. No Metal or thread environment tuning
is required. See the [API reference](api.md) for parameters.
