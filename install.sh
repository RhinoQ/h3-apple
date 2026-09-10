#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo "H3 Apple requires an Apple Silicon Mac." >&2
  exit 1
fi
conda_bin="${CONDA_EXE:-$(command -v conda || true)}"
if [[ -z "$conda_bin" ]]; then
  echo "Install Miniforge or Miniconda, then run ./install.sh again." >&2
  exit 1
fi
prefix="$root/.local/envs/h3"
if [[ ! -f "$prefix/conda-meta/history" ]]; then
  # A private cache plus copies keeps pip from modifying Conda's shared hardlinks.
  CONDA_PKGS_DIRS="$root/.local/conda-pkgs" "$conda_bin" create --yes --copy \
    --prefix "$prefix" --file "$root/environments/conda-osx-arm64.lock"
fi
"$prefix/bin/python" -m pip install --requirement "$root/environments/requirements.lock"
"$prefix/bin/python" -m pip install --no-deps --no-build-isolation "$root"
"$prefix/bin/python" -m pip check
echo "Installed. Activate with: conda activate $prefix"
echo "Fixed Python: $prefix/bin/python"
echo "Next: h3 doctor, then h3 models prepare"
