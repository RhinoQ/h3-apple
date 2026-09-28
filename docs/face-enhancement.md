# Optional small-face enhancement

Version 0.5.2 can enhance selected small faces in an existing H3 video. This is
an additional postprocessing operation. Ordinary `h3 generate` still uses the
0.5.1 native engine and does not install, import or load the restoration stack.

Watch the [original/restored comparison](https://rhinoq.github.io/h3-apple/previews/delegation-local-vosr/).
It demonstrates local detail, not an accepted narrative film: the source has
repeated gestures and an incorrectly directed farewell. Enhancement does not
repair those actions. Fine facial detail is reconstructed and can differ from
the source; exact identity or temporal fidelity is not guaranteed.

## Setup

Use the Python 3.11 Conda environment from [installation](install.md). The
optional PyTorch stack is tested with Python 3.11; it is not required for normal
generation. Install this exact release with its optional dependencies:

```bash
python -m pip install 'h3-apple[faces] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.5.3/h3_apple-0.5.3-py3-none-any.whl'
h3 prepare-faces --plan
h3 prepare-faces
```

The separate package contains **7.08 GB** of VOSR2, Qwen 2D VAE, DINOv2-L and
RetinaFace assets. Models default to `~/Models/h3-apple/faces`; they are not
bundled in the wheel or fetched on import. Every file has a pinned size and
SHA256. Downloads resume through the same verified downloader as H3. Review
[component terms](#component-terms) before use.

For an existing VOSR snapshot and RetinaFace cache, avoid duplicate downloads:

```bash
h3 prepare-faces --reuse-dir /path/to/vosr-weights --reuse-dir /path/to/retinaface-cache
```

The VOSR directory must retain the upstream `VOSR2/`, `Qwen-Image-vae-2d/` and
`torch_cache/checkpoints/` layout. The detector cache contains
`detection_Resnet50_Final.pth`. Same-volume reuse makes verified hard links;
cross-volume reuse copies the files. Use `--model-dir` on both preparation and
enhancement to keep these optional models on another volume. This directory
is separate from `h3 generate --model-dir`.

## Enhance

```bash
h3 enhance-faces --input video.mp4 --output enhanced.mp4
```

```python
from h3_apple import enhance_faces

result = enhance_faces("video.mp4", output="enhanced.mp4")
print(result.video_path, result.enhanced_frames, result.face_passes)
```

The operation accepts H3 576p/768p landscape or portrait MP4s: 24 fps, 8-bit
video, at most ten minutes, and zero or one AAC audio stream starting at zero.
Edited H3 sequences are supported. Original audio duration is preserved even
when an edit leaves an audio tail. Other dimensions, HDR, rotation metadata,
variable frame timing and multiple audio streams are rejected before inference.

The first pass finds and tracks faces. Eligible tracks have at least five
consecutive frames with a 32–160 pixel face box; large closeups and very small
or uncertain faces are skipped. A shot cut starts a new track. A single missed
frame is bridged only between unambiguous overlapping single-face detections.
No faces selected means a byte-identical copy of the source, without loading
VOSR. Multiple selected faces are processed sequentially.

The fixed recipe uses a stabilized 256-pixel source crop, a 512-pixel FP32 MPS
restoration canvas, one VOSR2 step and source-derived feathering. Users do not
need to choose crop size, denoise or seed. Pixels outside the masks are exact
before final H.264 encoding; the lossy delivery encode can change them. The
audio stream is copied and its decoded samples are checked for equality.

The API also accepts `model_dir`, `on_progress`, `diagnostics=False` and
`timeout=7200`. It returns an `EnhancementResult` with `video_path`,
`metadata_path`, `elapsed_seconds`, `enhanced_frames` and `face_passes`.
The `.faces.json` record identifies the source, recipe, models and environment.
Existing inputs and outputs are never overwritten. Ctrl-C/timeouts terminate
the worker process group; failed work retains diagnostics. Successful jobs
remove temporary frames unless `--diagnostics` is requested.

Enhancement shares the generation device lock: run one GPU job at a time.
The existing 40-core M5 Max/macOS 26.2+/64 GB product requirement remains;
measurements used 128 GB, not a smaller-memory machine. Connect AC power,
disable Low Power Mode and leave 20 GiB free disk. Serious thermal pressure or
more than 2 GiB additional swap stops the job. No 32 GB support is claimed.

## Cost and quality evidence

The accepted research recipe took **417.18 seconds** to process a 17.75-second
1024×576 film, with a **10.05 GiB** one-second sampled process-tree physical
footprint peak. It enhanced 234 of 426 frames, making 352 face passes across
four tracks. The 192 closeup frames received no restoration. Timing includes
loading, verification, tracking, restoration, diagnostics, export and validation;
it excludes one-time dependency/model setup. This is extra processing cost,
not a generator speedup or a typical cost for every clip.

The environment was a 40-core M5 Max, 128 GiB, macOS 26.6.1 and PyTorch 2.11.0
FP32 MPS. Non-blind review covered small-face motion, a profile, another
character/scene and sampled full-film crops. Sharper outlines can contrast with
motion-blurred surroundings. There is no sharp ground truth, universal identity
guarantee, or temporally conditioned restoration. The earlier 10% added-time
target was not met; the user accepted this measured cost for an optional pass.

Installed-package release checks are recorded in
[v0.5.2 release evidence](evidence/v0.5.2-release.json).
The final installed-wheel replay took **370.79 seconds**, with a **9.55 GiB**
sampled process-tree peak (one individual process reading used RSS fallback).
All 426 pre-encode RGB frames, selection geometry and the complete MP4 bytes
match the accepted comparison. The export scope differs from the earlier
research run, so these timings are not a controlled speedup comparison.

## Component terms

Models and upstream source retain their own terms. Source identities and local
modifications are recorded in [the component manifest](evidence/v0.5.2-source-components.json);
full notices and license texts ship with both the wheel and source distribution.

| Component | Upstream terms and scope |
| --- | --- |
| VOSR project-authored inference and checkpoints | Apache-2.0 according to the [VOSR model card](https://huggingface.co/CSWRY/VOSR); external components remain separate |
| Qwen/Wan 2D VAE, DINOv2 | Apache-2.0, original notices retained |
| LightningDiT, SiT, EVA/rotary embedding | MIT notices retained; LightningDiT also credits DiT source lineage |
| DiT source lineage | [CC BY-NC 4.0](https://github.com/facebookresearch/DiT/blob/main/LICENSE.txt); retained for inherited portions, not relicensed as Apache |
| RMSNorm source retained from VOSR | Llama 2 Community License and its required notice; no Llama language model or weights are bundled |
| RetinaFace/facexlib | Separate installed facexlib package and its upstream notices; detector weights downloaded from its pinned release |

The combined source package conservatively declares these component terms.
The optional restoration path is not represented as cleared for unrestricted
commercial use. These source terms are distinct from the separately downloaded
MiniMax generation model terms. See [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES).
