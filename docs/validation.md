# Validation

Version 0.5.0 moves installation to pip and shares automatic first-run setup
between the CLI and Python API. The inference engine, weights, adapter and
acceleration recipe remain pinned to the accepted identities. Its
[validation evidence](evidence/v0.5.0.json) records the two complete runs,
exact source identities, media-library hashes and package-validation boundary.

| Check | Result |
| --- | --- |
| Clean Python 3.11 and 3.14 environments, pip-installed dependencies | Passed |
| Runtime use with no system FFmpeg or Conda commands on PATH | Passed |
| Automatic model preparation from verified local weights | Passed; zero model-download bytes |
| Public CLI generation, three reference images | Passed; 124 frames, 1024×576, 24 fps, stereo 32 kHz audio |
| Public Python API generation in Python 3.14 | Passed; 120 frames / 5 seconds, including native-frame trimming |
| Four forwards, i8 + Sol + Sage, complete media decode | Passed in both runs |
| Unit, consent, subprocess, download and media tests | 78 passed |
| Wheel and sdist metadata, ordinary wheel installation | Passed |

The tests ran on M5 Max with 128 GB memory and macOS 26.6.1. The same
[complete prompt](evidence/ref2va-prompt.txt) and public references from the
0.4.0 case were used; the API test requests a 5-second delivery to exercise
trimming. These are installation and execution checks, not a new quality
ranking, controlled speed comparison or qualification of other hardware.
The original 145 GB model download was not repeated. Model preparation from
original weights retains the previous evidence below.

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
