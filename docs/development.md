# Development

h3-apple has one public path: still-image Ref2VA with four denoising forwards,
INT8 GEMM, Sol-Attn and SageAttention. The prompt and reference ordering are
preserved. Image preprocessing uses the output canvas area and 32-pixel
alignment. The 768p model canvas is center-cropped to the delivered dimensions;
extra model frames are trimmed with sample-accurate audio endpoints.

The Python layer owns input validation, model preparation, resource limits,
progress, cancellation, media validation and run records. The native engine
owns model execution and Metal kernels. `engine.py` builds one fixed graph;
there is no alternate inference backend or silent attention fallback.

The engine comes from the unmodified [vpipe source at the pinned commit](https://github.com/tgo-app-dev/vpipe/tree/f34e2cc3a3adae759eea254419f436f5b7800057).
Its authors and dependencies are credited in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES).
The product downloads and manages that engine internally; users do not need
another project or configuration interface.

## Verify a change

Development uses a project-local Conda environment. Users are also guided to use
Conda for Python and FFmpeg, with pip managing h3-apple and Pillow inside it.

```bash
conda create --prefix .local/envs/h3 -c conda-forge python=3.11 ffmpeg=8.1.2 pip -y
.local/envs/h3/bin/python -m pip install -r environments/dev.lock
.local/envs/h3/bin/python -m pip install --no-build-isolation .
.local/envs/h3/bin/python -I -m pytest tests -q
```

Tests use temporary files and synthetic media. A release also needs a normal
wheel installation, an actual model preparation or verified local reuse,
and a complete image-reference video through both public entry points. Keep execution,
quality judgments and performance comparisons as separate claims.

## Build the engine artifact

Check out the exact source revision above, including its submodules. Build
against FFmpeg 8 headers in a separate build environment, in Release mode:

```bash
conda create --prefix .local/envs/engine-build -c conda-forge ffmpeg=8.1.2
cmake -S /path/to/vpipe -B /path/to/build -DCMAKE_BUILD_TYPE=Release \
  -DVPIPE_METAL_RUNTIME_COMPILE=ON \
  -DVPIPE_FFMPEG_INCLUDE_DIRS="$PWD/.local/envs/engine-build/include"
cmake --build /path/to/build --target vpipe vpipe-cli -j 8
.local/envs/h3/bin/python tools/package_engine.py \
  --source-dir /path/to/vpipe --build-dir /path/to/build \
  --output /path/to/h3-apple-engine-macos-arm64.zip
```

Follow upstream build requirements for CMake and platform tools. Metal sources
are embedded in the library and compiled at runtime. The release CLI and library
link only to system libraries; at runtime FFmpeg 8 is loaded from the running
Python environment’s `lib` directory.
The artifact carries upstream licenses and notices. `data/engine.json` pins the
archive and every member by size and SHA256. Build identity is recorded, but
byte-identical compiler output across SDK versions is not promised.

Release source and wheel must contain identical Python/data files. The pinned
engine artifact is reused until its implementation changes. Do not bundle model
weights or user reference images in release assets.

## Publish the Python package

Build an sdist and wheel with `python -m build`, then check them with
`python -m twine check dist/*`. Verify installation from the wheel in a clean
Conda environment containing Python and FFmpeg, and test the documented CLI and
Python calls against real models before publishing a release.

The `publish.yml` workflow builds and checks the package on a version tag.
PyPI publication uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/):
run the workflow manually against that tag with `publish_to_pypi` enabled after
registering the publisher. Until then, users install the GitHub release wheel.
Register the GitHub owner `RhinoQ`, repository `h3-apple`, workflow `publish.yml`
and environment `pypi` in the PyPI project's publishing settings (or as a pending
publisher before the first release). This links the maintainer's PyPI account
without storing a long-lived API token in the repository. Uploads require a
tag whose version matches both the project metadata and the Python package.
