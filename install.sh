#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 0 ]]; then
  echo 'Usage: ./install.sh' >&2
  exit 2
fi
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo 'H3 Apple requires an Apple Silicon Mac.' >&2
  exit 1
fi
conda_bin="${CONDA_EXE:-$(command -v conda || true)}"
if [[ -z "$conda_bin" ]]; then
  conda_bin="$root/.local/miniforge/bin/conda"
  if [[ ! -x "$conda_bin" ]]; then
    mkdir -p "$root/.local/downloads"
    name='Miniforge3-26.7.2-0-MacOSX-arm64.sh'
    installer="$root/.local/downloads/$name"
    if [[ ! -f "$installer" ]]; then
      curl --fail --location --retry 3 --output "$installer.partial" \
        "https://github.com/conda-forge/miniforge/releases/download/26.7.2-0/$name"
      mv "$installer.partial" "$installer"
    fi
    (cd "$root/.local/downloads" && shasum --algorithm 256 --check "$root/environments/miniforge.sha256")
    bash "$installer" -b -p "$root/.local/miniforge"
  fi
fi
prefix="$root/.local/envs/h3"
if [[ ! -f "$prefix/conda-meta/history" ]]; then
  CONDA_PKGS_DIRS="$root/.local/conda-pkgs" "$conda_bin" create --yes --copy \
    --prefix "$prefix" --file "$root/environments/conda-osx-arm64.lock"
fi
"$prefix/bin/python" -m pip install --requirement "$root/environments/requirements.lock"
"$prefix/bin/python" -m pip install --no-deps --no-build-isolation "$root"
"$prefix/bin/python" -m pip check
printf '\nInstalled h3-apple. Preparing the model (existing weights are reused).\n'
"$root/h3" prepare
printf '\nReady. Generate with: ./h3 generate --image reference.jpg --prompt "Your scene"\n'
