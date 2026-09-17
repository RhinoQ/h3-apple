# Video references

The 0.1.0.dev11 development build adds `reference_videos` / `--reference-video`
to the [generation API](api.md#reference-videos). It uses the existing
[Ref2VA model bundle and pinned weights](ref2va.md#installation-and-models).
It retains the Ref2VA four-step weights and sampler. Requests containing video
use true Dense attention; T2VA, FL2VA and image-only Ref2VA retain their VSA recipes.

Video input support does not guarantee faithful editing or preservation.
A single animal-replacement case using Dense attention received user acceptance
for visuals and sound. A separate Dense removal test deleted the target backpack
but changed the source scenery, camera view and motion. The larger reference
canvas does not guarantee preservation. Its [prompt, source, settings and failure record](../benchmarks/results/ref2va-video-01/dense-preservation-failure.json)
remain available. The completed image-reference validation
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
Without separate audio files, the first enabled video with sound is Audio 1,
the second is Audio 2, and so on. [Independent audio files](ref2va-audio.md)
take the first Audio numbers when supplied. `--no-reference-video-audio`
disables video soundtracks while retaining those files. FFmpeg resampling is
not asserted numerically identical to Torchaudio. Reference audio conditions generation;
it is not simply copied into the final MP4.
Soundtrack decoding and the real audio encoder passed a component check.
The completed generation case uses one short, silent reference video; it does
not qualify soundtrack-conditioned output quality, voice preservation,
multiple-video quality, or image/video mixing quality.

## Reproducibility and cost

Run metadata records input hashes, prompt, seed, model and code identities,
the canvas policy, actual prepared sizes, decoded and VAE-retained frames,
reference geometry, condition hashes, attention statistics and phase timings.
The four-step path preserves reference latent rows and decodes only generated
rows. The public API selects Dense for any request containing video. A same-input
VSA trial retained an extra dog and changed the source motion; it was not adopted.
The public Dense regression reproduced the accepted MP4 byte for byte. Its
timing, the rejected VSA run, and the historical Dense timing are retained in
the [integration record](../benchmarks/results/ref2va-video-01/README.md).
These are single observations, not a repeatable speed ratio or a general
performance guarantee.

Larger references add both encoder work and attention tokens. A longer or
multi-video reference can substantially increase time and memory even when
the generated video has the same resolution and duration. Start with one short
reference and a five-second output. The ordinary progress bar, cancellation,
device lock and resource checks also apply to video-reference generation.

The implementation source for the canvas rule is
[Diffusers, pinned revision](https://github.com/huggingface/diffusers/blob/759164b7ad116e091e9d3e222211c9aa27d835f6/src/diffusers/modular_pipelines/minimax_h3/modular_pipeline.py).
See [source records](sources.json) for the encoder, layout and VSA provenance.
