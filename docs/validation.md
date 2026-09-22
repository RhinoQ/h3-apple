# Validation

Version 0.5.0 installs as a Python package in a Conda environment containing
Python and FFmpeg 8.1.2. The CLI and Python API share automatic first-run setup.
The [release evidence](evidence/v0.5.0-conda.json) records the complete input,
source and media-library identities, model verification, outputs and timing.

| Check | Result |
| --- | --- |
| Documented Conda Python + FFmpeg installation | Passed on Python 3.11 and 3.14 |
| Normal wheel installation, dependency checks and runtime preflight | Passed; Pillow is the only pip runtime dependency |
| Automatic model preparation from verified local weights | Passed; all 44 files match the pinned prepared-model manifest, zero model-download bytes |
| Public CLI generation, three reference images | Passed; 124 frames, 1024×576, 24 fps, stereo 32 kHz audio |
| Public Python API generation in Python 3.14 | Passed; 120 frames / 5 seconds, including native-frame trimming |
| Native media libraries and final processing | Passed; all seven libraries, ffmpeg and ffprobe use the running Python's Conda environment |
| Four forwards, i8 + Sol + Sage, complete media decode | Passed in both runs |
| Unit, consent, subprocess, download and media tests | 86 passed |
| Source, wheel and installed Python/data files | Identical across both complete runs and the release |

The checks ran on M5 Max with 128 GB memory and macOS 26.6.1. They use the
[complete prompt](evidence/ref2va-prompt.txt) and public references from the
0.4.0 integration case. The API requests a 5-second delivery to exercise trimming.
Both executions deliberately omit Conda tools from PATH and set an unrelated
CONDA_PREFIX; media discovery follows the actual Python interpreter.

These checks establish installation and complete execution, not a new quality
ranking, controlled speed comparison or qualification of other hardware. The
engine, weights, adapter and acceleration recipe remain pinned. The original
model download and quantization were not repeated; prior preparation evidence
is retained below. The release evidence also retains the initial synthetic-media
fixture timeout and its resolution before the passing suite.

## Version 0.4.0

Version 0.4.0 was checked on an Apple M5 Max with 128 GB unified memory and
macOS 26.6.1. The [machine-readable evidence](evidence/v0.4.0.json) includes
source identities, public reference-image URLs, the full request, output
checksums and measured media properties. The [complete prompt](evidence/ref2va-prompt.txt)
is retained without shortening.

| Check | Result |
| --- | --- |
| Fresh private Conda environment, ordinary package installation | Passed |
| Install with no existing Conda on PATH; automatic Miniforge bootstrap | Passed |
| Verified local model reuse | Passed; zero model-download bytes |
| Fresh source quantization, reusing original weights | Passed; all 44 prepared files match the accepted model SHA256 hashes |
| Unit, process-lifetime, download and real FFmpeg tests | 70 passed |
| Full three-image Ref2VA CLI generation | Passed; 254.59 seconds elapsed |
| Delivered video | 1024×576, 124 frames, 24 fps, 5.1667 seconds |
| Delivered audio | AAC stereo, 32 kHz, matching duration |
| Four actual denoising forwards; Sol and Sage enabled without fallback | Passed |
| Complete audio/video decode and validation | Passed |

The release keeps the previously tested i8 + Sol + Sage computation and
four-step Ref2VA adapter. Image sizing matches the output-area policy used
by the comparison case. This release changes installation and the product
interface; these checks do not establish a new quality ranking, a universal
speed record, exact audio-content compliance, or support for other chips.
The elapsed time is a single integration measurement, not a controlled
performance comparison. Equal seeds are inputs, not a promise of identical
GPU output bytes.

The earlier multi-method studies remain in the
[v0.3.0 source history](https://github.com/RhinoQ/h3-apple/tree/v0.3.0/docs/validation.md).
The same pinned engine, source weights and adapter identities make the
current generation path auditable without retaining the older product modes.
