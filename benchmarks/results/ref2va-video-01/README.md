# Video-reference integration

This record covers five-second 768p video-reference runs of the public
`generate()` API on Apple M5 Max / 128 GiB. It is an already observed calibration
example, not an independent or blind quality evaluation. No prompt, seed,
weight or sparsity search is performed.

## Results

The **0.1.0.dev11 public Dense default passed**: the complete MP4 is
byte-identical to the previously user-accepted Dense clip. Decoded video and
audio hashes, all reference conditions and initial noise also match. The
acceptance therefore applies to these exact media contents. It does not
establish reliable editing across other inputs.

| Run | Complete elapsed time | Result |
| --- | ---: | --- |
| Public Dense, dev11 | 31m 52s | 4 NFE, zero sparse calls; exact accepted MP4 reproduced |
| Same-input VSA trial, dev10 | 28m 27s | 4 NFE, 200 sparse calls; extra original dog and incorrect source motion |
| Earlier Dense baseline | 26m 19s | Same MP4 as public Dense; nonblind user acceptance for visuals and sound |

The VSA run had identical conditions and initial noise. All 120 frames were
reviewed nonblind, with native-resolution checks at frames 0 and 30. Two brown
capybara-like animals coexist with a residual gray/white dog, and the motion
already differs within the source-covered interval. VSA is not adopted for
video-containing requests. These single timings are retained as observations;
they do not establish a repeatable speed ratio. In particular, the newer VSA
run is faster than the newer Dense run, but it fails the editing requirements.

[results.json](results.json) records exact source, model, input, output,
condition and decoded-media identities, phase timings and execution checks.
The separate [Dense preservation failure](dense-preservation-failure.json)
retains its full prompt, input preparation and observed scenery/motion drift.
It was not rerun or reclassified during this integration.

## Reproduce

Use the pinned [Ref2VA model sources](../../../docs/ref2va.md#installation-and-models).
The reference is the first 56 frames (2.333 seconds) of DAVIS 2017's `dogs-jump`
sequence. Its source URL, checksums and exact preparation are in [input.json](input.json).
The source has no audio. Source-motion preservation is evaluated only while
the reference lasts; the remaining output is a generated continuation.

1. Download the [fixed source MP4](https://huggingface.co/datasets/emirkisa/DAVIS-2017-480p-mp4/resolve/06c7e6d99d6a7ddc7edbeaa6be838316feb70989/dogs-jump_raw_24fps.mp4) as `dogs-jump_raw_24fps.mp4`.
2. Prepare the exact reference with the Conda FFmpeg used by your installation:

```bash
ffmpeg -v error -i dogs-jump_raw_24fps.mp4 -map 0:v:0 -an -frames:v 56 -c:v libx264 -crf 16 -pix_fmt yuv420p reference.mp4
```

3. From the repository root, generate using the [complete prompt](prompt.txt):

```bash
h3 generate --task ref2va --prompt-file benchmarks/results/ref2va-video-01/prompt.txt --reference-video reference.mp4 --model-dir ~/Models/h3-apple-ref2va --resolution 768p --duration 5 --seed 1103 --output capybaras.mp4
```

The prompt is:

> Edit Video 1 into a continuous five-second photorealistic outdoor shot. Replace each of the two dogs with one brown capybara, keeping two animals in total, and remove both original dogs completely. The two capybaras inherit the two dogs’ separate screen positions, directions, and motion paths as they move around the woman. Adapt their legs and gait to believable capybara anatomy. Preserve the woman in the green top, her identity, clothes, gestures and position, as well as the grass field, distant tree line, cloudy sky, low camera angle and camera movement. Follow the reference action during its first 2.33 seconds, then continue the same scene naturally to five seconds. Do not add animals, people, cuts, captions, or a title. Natural outdoor ambience and soft footsteps on grass, with no dialogue or music.

FFmpeg build differences can change encoded-file hashes. The run record also
records the prepared RGB, encoded reference and initial-noise hashes, so file
identity and numerical input identity can be checked separately.

## Compatibility scope

The installed package passed 261 tests, including all three public tasks,
video/image mixing, task conflicts, rotation, soundtrack decoding, control-token
and MRoPE layout, frozen reference rows, and five engine dispatch cases.
The T2VA vendor runtime, sparse kernels, VAE, image pipeline, FL2VA v1.2 pipeline
and shared encoders/sampler are unchanged; [file identities](unchanged-runtime.json)
record that check. This integration does not repeat full generation on those
unchanged routes; their earlier completed regressions remain separate evidence.

An initial public run stopped before conditioning because the audio encoder
path was resolved from an absent bundle field. The fix uses the verified
components directory; a dedicated engine-dispatch regression covers it. The
failed attempt was retained and was not counted as a generated video.
