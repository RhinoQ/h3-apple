# Video references

The 0.1.0.dev10 development build adds `reference_videos` / `--reference-video`
to the [generation API](api.md#reference-videos). It uses the existing
[Ref2VA model bundle and pinned weights](ref2va.md#installation-and-models).
No new LoRA, gate, sampler, or output-resolution recipe is introduced.

Video input support does not guarantee faithful editing or preservation.
A single animal-replacement case using Dense attention received user acceptance
for visuals and sound. A separate Dense removal test deleted the target backpack
but changed the source scenery, camera view and motion. The larger reference
canvas does not guarantee preservation. The completed image-reference validation
does not establish video quality or support on smaller-memory Macs. Successful
decoding and completion of four steps are execution checks only.

## Input contract

Supply 1–3 local videos of 2–15 seconds, each with one video stream, square
pixels, and at most one soundtrack. Source aspect ratios from 1:4 to 4:1 are
accepted. Right-angle display rotation is applied during decoding. Output is
still landscape, 768p by default; `--resolution 576p` changes output geometry,
not the reference canvas. Ordered images may accompany videos.

Each video is sampled at 24 fps. Its reference canvas follows the released H3
rule: start with a 768-pixel short edge, cap area at `768*1344`, then round both
axes to the nearest 32. Final rounded area can be slightly larger than the cap.
For example, 854×480 becomes 1344×768. Upscaling changes the model's input grid;
it does not restore detail absent from the source. Image references retain
their existing 258,048-pixel budget by default; `--reference-resize match`
instead uses the output canvas area for images. Neither changes the video rule.

Qwen samples every twelfth decoded frame and groups timestamps in pairs. The
native video VAE retains the longest prefix with `17*n+5` frames. Both start
from the same prepared RGB frames. Decoding caps reference duration at the
model's generation duration; a shorter input is not looped or stretched. The
model generates the continuation, so motion after the source ends has no
reference ground truth.

A soundtrack is resampled to 32 kHz stereo and included as an audio reference.
The first video with sound is Audio 1, the second with sound is Audio 2, and so
on. FFmpeg resampling is not asserted numerically identical to Torchaudio.
Standalone audio input is not exposed. Reference audio conditions generation;
it is not simply copied into the final MP4.

## Reproducibility and cost

Run metadata records input hashes, prompt, seed, model and code identities,
the canvas policy, actual prepared sizes, decoded and VAE-retained frames,
reference geometry, condition hashes, attention statistics and phase timings.
The four-step path preserves reference latent rows and decodes only generated
rows. The public API selects VSA. The Dense example's acceptance must not be
treated as general VSA quality acceptance. Dense remains an explicit
internal comparison path, not a user-facing quality preset.

Larger references add both encoder work and attention tokens. A longer or
multi-video reference can substantially increase time and memory even when
the generated video has the same resolution and duration. Start with one short
reference and a five-second output. The ordinary progress bar, cancellation,
device lock and resource checks also apply to video-reference generation.

The implementation source for the canvas rule is
[Diffusers, pinned revision](https://github.com/huggingface/diffusers/blob/759164b7ad116e091e9d3e222211c9aa27d835f6/src/diffusers/modular_pipelines/minimax_h3/modular_pipeline.py).
See [source records](sources.json) for the encoder, layout and VSA provenance.
