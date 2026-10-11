# Add detail with VOSR

Add `--upscale` when generating. H3 chooses native 768p, generates the video,
then doubles its width and height while preserving audio.

```sh
h3 generate --image reference.jpg \
  --prompt "A slow cinematic push-in on Picture 1. Soft ambient music." --upscale
```

Requires the [standard installation](install.md), **128 GiB memory**, and at least
20 GiB free working space. First use downloads **6.97 GB** of models; later runs
reuse them.

Both videos are saved in a new `runs/` folder. To choose the final filename, add
`--output detailed.mp4`; the original is saved as `detailed.native.mp4`.

## Existing video or retry

```sh
h3 upscale --input native.mp4
```

The result goes into a new `runs/` folder. Use this command to retry restoration
after a failure without generating again. Add `--output detailed.mp4` for a specific
filename or `--duration 5` to process the first five seconds of a longer clip.

## Input and output

| Native input | Upscaled output |
| --- | --- |
| 1366×768 | 2732×1536 |
| 768×1366 | 1536×2732 |
| 1024×576 | 2048×1152 |
| 576×1024 | 1152×2048 |

The combined command selects native 768p automatically. For separate steps,
generate with `--resolution 768p --no-x2` or `--resolution 576p --no-x2`.
Inputs must be 24 fps, up to 15 seconds, with AAC audio or no audio. X2 output
is already larger and is outside this restoration profile.

The two five-second 768p showcases took about **20 minutes each** to upscale
on a 40-core M5 Max / 128 GiB. That is additional to generation. N8 restoration
fell from **46m 30s to 20m 11s: 56.6% less time** than the FP32 reference.
[Measurements and limits](evidence/v0.8.0-vosr.json) ·
[Watch N8 and N6](https://rhinoq.github.io/h3-apple/#showcase).

VOSR can add plausible detail; it cannot repair a failed action or guarantee
faithful text, faces or architecture. Review motion and fine patterns in the result.
The restored video uses H.264; audio is copied without re-encoding.

## Python

```python
from h3_apple import upscale

result = upscale("native.mp4")
print(result.video_path)
```

For generation and restoration in one call, use `generate(..., upscale=True)`.

Optional arguments: `output=None`, `duration=None`, `model_dir`, `on_progress`, `diagnostics=False`,
`timeout=14400` seconds. `UpscaleResult` contains `video_path`, `metadata_path`
and `elapsed_seconds`; model preparation is outside that timer. Existing outputs
are refused; failures retain logs. The fixed recipe replays seed-42 noise across
frames for consistency.

<details>
<summary>Reuse models or choose their location</summary>

```sh
h3 prepare-vosr --plan
h3 prepare-vosr --reuse-dir /path/to/existing-vosr-models
```

Default directory: `~/Models/h3-apple/vosr`. Set `H3_VOSR_MODEL_DIR` or pass
`--model-dir` to both preparation and upscaling. Reused files must match the
pinned checksums. Downloads resume on retry.
For `h3 generate --upscale`, use `--upscale-model-dir` instead; `--model-dir`
continues to select the generation models.

</details>

## Credits and terms

[VOSR](https://github.com/cswry/VOSR) supplies the restoration model and pipeline;
Qwen-Image VAE and DINOv2 supply its image components. We adapted the pipeline
for Apple GPUs, reduced repeated conversion and GPU dispatch overhead, and
packaged video/audio handling with reproducible run records.

The bundled restoration components include **CC BY-NC 4.0** code inherited by
LightningDiT, so this feature is for **noncommercial use** under the retained
component terms. [Full attribution and licenses](../THIRD_PARTY_NOTICES).
