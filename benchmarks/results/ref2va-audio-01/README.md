# Independent audio-reference integration

This record tests the public Ref2VA `reference_audio` API using one image and
one independent recording. It is a new calibration composition made from
already observed fal guide assets, not a reproduction of fal's original case,
a held-out test or a blind quality comparison.

## Result

The **0.1.0.dev12 public audio-reference run passed execution validation**.
It produced a complete six-second 1366×768 / 24 fps video with 32 kHz stereo
audio in **23m 13s (1392.610s)** on M5 Max / 128 GiB. All six reference arrays
match the dev11 private encoder exactly. The 482 audio reference rows and 880
visual reference rows remain fixed through all four steps; there are zero
VSA calls and all 20 block progress events are present.

[Exact results](results.json) record the measured source, weights, conditions,
output identity, timings and memory. Peak MLX allocation was 33.44 GiB with no
swap growth; this does not qualify a smaller-memory machine. Diagnostics were
enabled and their measured export time is retained. No baseline full generation
was run, so this timing is not a speed comparison.

[Nonblind review](review.json) found no gross face collapse or extra subject
across all 144 frames. The camera gradually pushes in despite the steady-camera
instruction. Local English ASR returns “Please stay with me.”, the requested
line; it does not establish voice similarity or synchronization. Human
listening acceptance is pending. The clip has not been publicly uploaded.

## Reproduce

Use the [Ref2VA model bundle](../../../docs/ref2va.md#installation-and-models)
and this development version. No additional H3 checkpoint is needed. The
input audio is about six seconds, so the output is six seconds at 768p. The
model pads to 158 frames internally and delivers 144 frames. `match` keeps
more reference image detail than the legacy image budget; it does not add
information absent from the source.

[Input identities and preparation](input.json) preserve the source URLs,
SHA-256 values and the first-frame extraction rule. The image is frame zero
of the [source video](https://v3b.fal.media/files/b/0aa44050/8CO6x9AT6pdNGg9CroOYt_3-3-3-1_in2.mp4).
The [separate audio recording](https://v3b.fal.media/files/b/0aa44040/RgapPrm2v-i7pGLrCZtwv_3-3-3-1_in1.mp3)
is used as Audio 1. Its spoken words and language are not assumed from the
English guide. The intended English line is specified anew in the prompt.

From the product checkout, using the installed Conda tools:

```bash
curl -L --fail 'https://v3b.fal.media/files/b/0aa44050/8CO6x9AT6pdNGg9CroOYt_3-3-3-1_in2.mp4' -o source.mp4
curl -L --fail 'https://v3b.fal.media/files/b/0aa44040/RgapPrm2v-i7pGLrCZtwv_3-3-3-1_in1.mp3' -o voice.mp3
.local/envs/h3/bin/ffmpeg -v error -i source.mp4 -map 0:v:0 -frames:v 1 picture.png
.local/envs/h3/bin/python -m h3_apple generate --task ref2va --reference-image picture.png --reference-audio voice.mp3 --prompt-file benchmarks/results/ref2va-audio-01/prompt.txt --model-dir ~/Models/h3-apple-ref2va --resolution 768p --reference-resize match --duration 6 --seed 42 --output dialogue.mp4
```

Verify downloaded media against `input.json` before reproducing. The complete
[prompt file](prompt.txt) contains:

> Use Picture 1 for the woman's appearance, dark hair, pale grey top, and the waterfront setting at dusk. Use Audio 1 as a reference for her voice timbre and emotional delivery. Create one continuous six-second photorealistic close-up of the same woman, with the softly blurred waterfront lights behind her. She looks toward someone just beside the camera, breathes naturally, and says clearly in English, "Please stay with me." Her expression is tender and earnest. Keep her face large and sharply focused, with gentle natural head and lip movement and a steady camera. Keep exactly one woman in the shot. After the line she holds a quiet gaze. Generate quiet waterfront ambience beneath her voice. No music, subtitles, on-screen text, or cuts.

## What is checked

The installed wheel passed **286 tests**, dependency checking and readiness
checks for all three task bundles. Tests cover audio validation, mono/stereo
decoding, reference limits, task conflicts, ordered audio labels, soundtrack
selection, input snapshots, cache identity and seven engine dispatch cases.

The numeric control runs the frozen previous version's existing private
mixed encoder with identical files, prompt, geometry and seed. The public
candidate must reproduce all six exported condition arrays exactly. The full
run also checks fixed video/audio reference rows in all four denoising steps,
identical initial generated noise, four NFE, zero VSA calls, all 20 block
progress events, runtime/model identities and full audiovisual decoding.
This control is not a baseline full generation or a paired timing experiment.

A separate [real-file soundtrack selection check](soundtrack-selection.json)
uses the same source video and audio over 53 decoded frames. Disabling video
soundtracks preserves the prepared visual frames and explicit audio exactly.
It verifies media preparation only, without another generation or a claim
about multiple voices and perceptual source separation.

The [runtime comparison](unchanged-runtime.json) records 44 unchanged files
and eight changed files. All vendor kernels, video/audio VAE, image-only and
FL2VA encoder/sampler code are unchanged. Public dispatch and mixed audio
selection/metadata changed. Earlier full T2VA, FL2VA and image-reference
results retain their original scope; those generations are not repeated here.

## Quality boundary

The input audio conditions newly generated sound; it is not copied into the
output. Numeric parity and a completed MP4 do not establish voice similarity,
intelligibility, lip synchronization or reliable editing. Visual observations,
any ASR output and actual human listening acceptance are recorded separately
in the completed run report. Single-run timing is an observation only.
