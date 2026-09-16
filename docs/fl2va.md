# First/last-frame video with audio

FL2VA accepts a first frame, a last frame, or both through the same CLI/API as
T2VA and Ref2VA. It defaults to 768p and uses four-step LightX2V v1.2 with VSA.
Use clear source images and 768p for small faces. These are conditioning anchors,
not a guarantee of pixel-identical endpoints or every intermediate pose.

## Model recipe

| Component | Pinned source and use |
| --- | --- |
| Native base and encoders | [MiniMax-H3 FL2VA](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/FL2VA); clean 13-shard base, processor, tokenizer, text/vision encoder and native image VAE |
| Four-step LoRA | [LightX2V FL2V v1.2 768p BF16](https://huggingface.co/lightx2v/Minimax-h3-Turbo/blob/3ec17a324ced54151364f24f8b5fb6bf7e26414f/minimax_h3_fl2v_turbo_4step_v1.2_768p_bf16.safetensors); 1,383,677,808 bytes, rank 128, alpha 8, 624 tensors |
| VSA gates | [FastH3 VSA Data-Free adapter](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-LoRA/blob/bcf40ca6f457ed66f8badf13514943e390205fca/vsa-datafree/adapter_model.safetensors); only 50 compression gates, no T2VA LoRA or exact-delta updates |
| Decoders | Reuse the prepared T2VA bundle's native video/audio decoder components |

LoRA SHA256: `c3d4a2cf618efea71b9e21a4baaa12d412f1eb6c2b6f86efacaf0ebb6814b689`.
The [official v1.2 settings](https://huggingface.co/lightx2v/Minimax-h3-Turbo/discussions/52)
are **4 NFE, video shift 6, audio shift 3, Euler, up to 768p**. The release focuses
on audio improvements over v1.1; that does not establish improved faces, layout,
or audio quality for this separate MLX/VSA combination.

## Prepare and generate

Install with `./install.sh --ref2va` and activate the printed Conda environment.
Reuse the [pinned source snapshots and converted decoder](models.md). The native
FL2VA directory must expose `transformer`, `processor`, `tokenizer`,
`text_encoder`, and `video_vae`. Keep existing bundles intact and use new output
directories. Run the following with that environment's fixed Python:

```bash
MLX_ENABLE_TF32=0 python -m h3_apple.conversion --task fl2va --native /path/to/FL2VA --adapter /path/to/minimax_h3_fl2v_turbo_4step_v1.2_768p_bf16.safetensors --gate-source /path/to/vsa-datafree/adapter_model.safetensors --components /path/to/text-bundle/components --output /path/to/new-fl12-conversion
h3 models prepare --checkpoint /path/to/new-fl12-conversion/dit --components /path/to/text-bundle/components --fl2va-native /path/to/FL2VA --model-dir ~/Models/h3-apple-fl2va-v12
h3 models verify --model-dir ~/Models/h3-apple-fl2va-v12
h3 generate --task fl2va --prompt-file prompt.txt --first-frame first.png --last-frame last.png --model-dir ~/Models/h3-apple-fl2va-v12 --resolution 768p --duration 5 --seed 42 --output keyframes.mp4
```

Conversion fuses the new LoRA into the native base before INT8/group64 storage,
rebuilds AdaLN at the 6/3 timesteps, and records the pinned recipe. Do not add
v1.2 on top of an already fused v0.1 model. The converter sets its own arithmetic
architecture override; generation restores the physical GPU architecture.

The complete prompt is retained. With two inputs, first and last are Picture 1
and Picture 2; with a single input it is Picture 1. The first supplied anchor is
stretched to the model canvas, and the second is cover-cropped. Each has a
separate protected VSA prefix and its corresponding target time. Only generated
rows are decoded. Delivery trims the padded native frame count to the requested
duration; the last anchor guides the padded endpoint, not a forced last-frame
pixel copy.

## Validation scope

VSA uses the Ref2VA-style protected prefix, 75% nominal sparsity and Kablex
routing. Runs require all 200 sparse block calls without Dense fallback and
record actual statistics, input hashes, sampling recipe, code/model identity,
phase timings and complete media validation. This is a gate transfer to FL2VA,
not an officially jointly distilled LightX2V/VSA checkpoint.

A [five-second 768p first/last-frame integration case](../benchmarks/results/fl2va-v12-01/README.md)
completed with 4 NFE and 200 sparse calls on M5 Max / 128 GiB. All 120 frames
received a limited nonblind visual review; the result, full prompt, source
frames, hashes, command and remaining quality limits are recorded there.
Previous FL2VA v0.1 outputs do not qualify the new weights. No broad quality,
Dense-equivalence, speedup or smaller-memory-hardware claim is made.
