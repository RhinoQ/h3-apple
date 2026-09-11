# Installation and your first video

The tested system is **Apple M5 Max / 128 GiB / macOS 26.6.1**. This build requires
M5, at least 96 GiB of unified memory, and macOS 26.2 or later. A 96 GiB machine
has not completed end-to-end validation. Keep at least 20 GiB of disk space free
for generation, in addition to model storage. Run on AC power.

## Conda environment

Install ARM64 [Miniforge](https://github.com/conda-forge/miniforge), or use an
existing ARM64 Conda installation. Then run:

```bash
git clone https://github.com/RhinoQ/h3-apple.git
cd h3-apple
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 --version
```

The installer uses the readable [environment definition](../environments/environment.yml)
and exact [osx-arm64 lock](../environments/conda-osx-arm64.lock). It creates a
private Conda cache and environment, with Python 3.11.15, MLX 0.32.0, FFmpeg 8.1.2,
and locked Python dependencies. It installs a regular wheel without changing
system Python or user site-packages. PyTorch and external benchmark projects
are not required.

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
h3 generate --prompt "A paper boat drifts across a quiet pond. Soft water sounds and birdsong." --output boat.mp4
```

The default is a native 768p, 15-second, 24 fps video with stereo audio. For a
smaller first check:

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
