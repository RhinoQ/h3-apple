# Face enhancement

Restore selected small faces in an existing H3 video. This optional pass adds
processing time and may change identity or flicker; it cannot repair failed actions.

## Setup

In the [Python 3.11 H3 environment](install.md), install the optional dependencies:

```sh
python -m pip install "h3-apple[VSA,faces] @ https://github.com/RhinoQ/h3-apple/releases/download/v0.7.0/h3_apple-0.7.0-py3-none-any.whl"
h3 prepare-faces --plan
h3 prepare-faces
```

The **7.08 GB** model set downloads to `~/Models/h3-apple/faces`.
Ordinary generation does not load it. Review [component terms](#component-terms).

<details>
<summary>Reuse models or change their location</summary>

```sh
h3 prepare-faces --reuse-dir /path/to/vosr-weights --reuse-dir /path/to/retinaface-cache
```

Keep the upstream `VOSR2/`, `Qwen-Image-vae-2d/` and `torch_cache/checkpoints/`
layout. RetinaFace needs `detection_Resnet50_Final.pth`.
Reuse verifies hashes, hard-links on one volume and copies across volumes.
Pass `--model-dir` to both preparation and enhancement for a custom location,
separate from generation models. Downloads resume and verify pinned checksums.

</details>

## Enhance

```sh
h3 enhance-faces --input video.mp4 --output enhanced.mp4
```

```python
from h3_apple import enhance_faces

result = enhance_faces("video.mp4", output="enhanced.mp4")
print(result.video_path, result.enhanced_frames, result.face_passes)
```

**Input:** H3 native 576p/768p landscape or portrait MP4, 24 fps, 8-bit,
up to ten minutes, with zero or one AAC stream starting at zero. Edited H3
sequences are supported. X2 dimensions, HDR, rotation metadata, variable frame
timing and multiple audio streams are rejected.

Faces qualify at **32–160 pixels for at least five consecutive frames**.
Cuts reset tracking; only unambiguous single-frame gaps are bridged.
Large closeups, tiny and uncertain faces are skipped. No selected faces produces
a byte-identical copy without loading VOSR.

Audio is copied, including any edit tail, and decoded samples are verified.
Pixels outside restoration masks are unchanged before lossy H.264 encoding.

<details>
<summary>Recipe, API and resource limits</summary>

The fixed recipe uses a stabilized 256-pixel crop, 512-pixel FP32 MPS canvas,
one VOSR2 step and source-derived feathering. Multiple faces run sequentially.

The API accepts `model_dir`, `on_progress`, `diagnostics=False` and `timeout=7200`.
Results contain `video_path`, `metadata_path`, `elapsed_seconds`,
`enhanced_frames` and `face_passes`. The `.faces.json` record identifies
source, recipe, models and environment.

Existing files are never overwritten. Cancellation stops the worker group.
Failed jobs retain diagnostics; successful runs remove frames unless requested.
One GPU job runs at a time. Use AC power, disable Low Power Mode and allow
20 GiB temporary disk. Serious thermal pressure or over 2 GiB extra swap stops
the job. Standard product hardware requirements apply.

</details>

## Cost and quality evidence

One **17.75-second, 1024×576** clip on M5 Max / 128 GiB, macOS 26.6.1,
PyTorch 2.11.0 FP32 MPS:

| Run | Total processing | Sampled peak memory |
| --- | ---: | ---: |
| Accepted research recipe | 417.18 s | 10.05 GiB |
| Installed-wheel replay | 370.79 s | 9.55 GiB |

The recipe restored 234 of 426 frames, with 352 passes across four tracks;
192 closeup frames were skipped. Costs include loading through validation,
excluding dependency/model setup. The export scopes differ, so the times
do not establish a speedup. The original 10% added-time target was not met.

[Release evidence](evidence/v0.5.2-release.json) records matching pre-encode RGB,
selection geometry and complete MP4 bytes in the replay. Memory was sampled
every second across the process tree; one replay reading used RSS fallback.

Non-blind review covered small faces, profile motion, another character/scene
and sampled film crops. There is no sharp ground truth or temporal conditioning.
Sharper faces may contrast with motion blur. Narrative errors in the source
remained; local detail improvement did not qualify the full film.

## Component terms

[Component identities and modifications](evidence/v0.5.2-source-components.json)
and full notices ship with source and wheel.

| Component | Upstream terms and scope |
| --- | --- |
| VOSR project-authored inference and checkpoints | Apache-2.0 according to the [VOSR model card](https://huggingface.co/CSWRY/VOSR); external components remain separate |
| Qwen/Wan 2D VAE, DINOv2 | Apache-2.0, original notices retained |
| LightningDiT, SiT, EVA/rotary embedding | MIT notices retained; LightningDiT also credits DiT source lineage |
| DiT source lineage | [CC BY-NC 4.0](https://github.com/facebookresearch/DiT/blob/main/LICENSE.txt); retained for inherited portions, not relicensed as Apache |
| RMSNorm source retained from VOSR | Llama 2 Community License and its required notice; no Llama language model or weights are bundled |
| RetinaFace/facexlib | Separate installed facexlib package and its upstream notices; detector weights downloaded from its pinned release |


The combined package is not cleared for unrestricted commercial use.
These source terms are separate from MiniMax generation-model terms.
See [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES).
