# Reference-conditioned video with audio

H3 Apple exposes Ref2VA through `h3 generate`
and the Python API. Supply 1–9 still images in picture-number order and/or
[1–3 reference videos](ref2va-video.md), optionally with [independent audio](ref2va-audio.md).
Image-only generation defaults to 576p; requests with videos or independent
audio default to 768p. All use four steps and default to
15 seconds; start with five seconds.
The complete prompt is retained, including any picture numbers it contains.

The current **0.2.2 source** recommends the pinned silveroxides DARE/TIES
`fro0995` adapter at strength **1.0**. It retains the four-step, video/audio
shift **12/3** recipe. Existing LightX2V v0.1 bundles remain supported;
installing software alone does not replace their weights. Select a separately
prepared DARE/TIES bundle with `--model-dir` to use the new adapter.

DARE/TIES was preferred by the user in two known fifteen-second 768p image
reference cases. Both still had defects, including duplicated people; one
showed late facial deformation. These preferences were reported after adapter
identities had been disclosed and are not confirmed blind votes. They do not
establish general quality, audio quality, synchronization or video/audio-reference
quality. See the [adapter evaluation record](evidence/ref2va-dareties.json).

With the earlier LightX2V v0.1 bundle, one-image / five-second and
four-image / fifteen-second cases at 576p have
completed on M5 Max / 128 GiB and received user quality acceptance. This is a
limited case review, not a broad or blind quality evaluation. A later
[one-image 768p portrait check](validation.md#portrait-and-dense-follow-up-2026-09-18)
also completed with `--reference-resize match`; fixed-frame inspection does
not extend the earlier user quality acceptance. Other image counts, general
768p quality, and smaller memory capacities remain unqualified.
Video-reference quality has a separate, limited validation scope;
see [video-reference limitations](ref2va-video.md). Audio files require an image
or video and have a [separate validation scope](ref2va-audio.md).

## Installation and models

From the current source checkout, install the optional CPU vision
dependencies with `./install.sh --ref2va`, then activate the printed Conda path.
DARE/TIES requires the 0.2.2 source or a later version. The
[published v0.2.1 installation](install.md) supports the earlier LightX2V
bundle; its release links do not yet provide DARE/TIES support.

Ref2VA uses a separate model bundle. The ordinary text model and automatic
`h3 models prepare` downloader remain the text-generation recipe. For Ref2VA,
reuse or obtain these pinned sources:

| Component | Source and use |
| --- | --- |
| Native transformer and reference encoders | [MiniMax-H3 Ref2VA](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/Ref2VA): 13 transformer shards, processor, tokenizer, Qwen vision/language weights and video VAE encoder |
| Recommended four-step adapter | [silveroxides Ref2V DARE/TIES fro0995](https://huggingface.co/silveroxides/MiniMax-H3_tests/resolve/16f950c2e3d78440778fe1e84d9179932e19b1de/ref2v_dareties/minimax_h3_ref2v_turbo_4step_v0.1_v4_step600_dareties_fro0995.safetensors): 259 dynamic-rank pairs, normalized alpha, strength 1.0 |
| VSA compression gates | [FastH3 VSA Data-Free adapter](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-LoRA/resolve/bcf40ca6f457ed66f8badf13514943e390205fca/vsa-datafree/adapter_model.safetensors): only the 50 compression-gate tensors |
| Output decoders | Reuse the prepared text bundle's H3 video/audio decoder components; original [MiniMax FL2VA sources](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/FL2VA) |

Keep source snapshots read-only and follow the [model terms and storage guidance](models.md).
Use a new output directory when converting:

```python
from h3_apple.conversion import convert_dit

convert_dit(
    "/path/to/Ref2VA/transformer",
    "/path/to/minimax_h3_ref2v_turbo_4step_v0.1_v4_step600_dareties_fro0995.safetensors",
    "/path/to/new-ref2va-checkpoint",
    print,
    task="ref2va",
    adapter_flavor="dareties-fro0995",
    gate_source="/path/to/vsa-datafree/adapter_model.safetensors",
)
```

Run conversion with the installed environment's fixed Python, setting
`MLX_ENABLE_TF32=0 MLX_METAL_GPU_ARCH=applegpu_g16s` before starting Python, as
required by the validated conversion arithmetic. Do not keep the conversion
architecture override when generating; the generation worker sets the M5 runtime.
Conversion writes `ref2va_recipe.json` and refuses an existing checkpoint path.
It merges the Ref2V LoRA before INT8/group64 conversion and selects only the
50 FastH3 gates; FastH3 T2VA low-rank and exact-delta updates are not applied.
The adapter's published alpha normalization is already incorporated: do not
apply a second alpha/rank factor. Conversion validates the exact source hash,
maps the fused ComfyUI QKV/FF layouts and all 51 AdaLN targets, and recomputes
the four-step AdaLN tables. Other compression variants are not interchangeable.

To reproduce an older bundle, use the pinned
[LightX2V Ref2V Turbo v0.1 file](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/ec01fa4c86263832faa0bd1d6d8f36a281eaabb2/minimax_h3_ref2v_turbo_4step_v0.1_bf16.safetensors)
with `adapter_flavor="lightx2v"` and a different output directory. Its rank-128,
alpha-8 scaling remains unchanged. Keep that bundle for rollback rather than
editing an existing model directory.

Import the converted checkpoint and native reference components:

```bash
h3 models prepare --checkpoint /path/to/new-ref2va-checkpoint --components /path/to/text-bundle/components --ref2va-native /path/to/Ref2VA --model-dir ~/Models/h3-apple-ref2va
h3 models verify --model-dir ~/Models/h3-apple-ref2va
h3 generate --prompt-file prompt.txt --reference-image reference-1.jpg --reference-image reference-2.jpg --model-dir ~/Models/h3-apple-ref2va --duration 5 --seed 42 --output reference-film.mp4
```

The bundle owns the encoders and recipe through verified hard links on the same
filesystem, or verified copies across filesystems. Generation works offline
after import and does not depend on the original source filenames. Do not edit
hard-linked files: their content is shared. Selecting a text bundle for a
reference request, or a reference bundle for a text request, returns an error.

## Recipe and scope

Both image encoders receive the same aspect-preserving RGB pixels, with a
258,048-pixel budget per image and dimensions aligned to 32. Each image keeps
its own latent prefix and dense-exempt attention segment. References are not
combined into a collage. Only generated latent rows enter the output decoders.

### Image size policy

`--reference-resize legacy` remains the default so existing results retain their
input policy. `--reference-resize match` instead uses the generated model
canvas's area as each reference's budget. Both keep aspect ratio, round to the
nearest 32 pixels, and avoid upscaling except for that grid rounding. A
1920×1080 reference becomes 672×384 with the legacy budget and 1376×768 for a
768p `match` request. A 320×192 reference stays 320×192 in either mode.

Reducing a reference too far can discard small faces, fine text and object
details before either encoder sees them. More pixels also add encoding work,
reference tokens and attention cost; they cannot restore missing source detail
or guarantee successful edits. The optional `match` policy follows the
[LightX2V training/inference recommendation](https://github.com/ModelTC/Minimax-H3-Turbo/blob/02e26d591f7a04d5d1a074c9566d5dd4f22f6225/README.md#note-on-reference-image-resizing).
Its end-to-end quality is not inferred from video-reference experiments or the
legacy image reviews above. The actual policy, budget and prepared image hashes
are recorded in every run. FL2VA keyframes already use the full model canvas
and do not use this Ref2VA image budget.

Image-only Ref2VA uses VSA with 64-token tiles and 75% nominal sparsity. Following Kablex /
Comfy Kitchen routing, it rounds the non-sink top-k budget, keeps ties and
neighboring tiles, and exempts prefix queries/keys. Actual sparsity and fallback
counts are recorded separately. Text generation retains its FastH3 route.
Requests containing video use true Dense attention after a video VSA trial
failed removal and motion-preservation checks. The same bundle is reused, but
its compression gates are disabled for that path; see [video references](ref2va-video.md).
Independent audio also starts with Dense; it does not inherit VSA quality qualification.

The implementation uses Ours INT8/group64 and BF16, native H3 decoding and NumPy
seed streams. It does not reproduce ComfyUI ConvRot/NVFP4, CUDA arithmetic or
CUDA RNG, and should not be described as FP32-equivalent. See the pinned
[implementation sources](sources.json) and [validation](validation.md).
