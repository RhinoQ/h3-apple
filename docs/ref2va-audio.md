# Independent audio references

The development API accepts `reference_audio=[...]` / repeated
`--reference-audio` arguments together with at least one Ref2VA image or video.
It uses the existing [Ref2VA model bundle](ref2va.md#installation-and-models),
four-step weights and audio encoder. No additional H3 checkpoint is required.
This does not add a fourth task or change the T2VA/FL2VA model recipes.

## Generate

```bash
h3 generate --task ref2va --reference-image character.png --reference-audio voice.wav --prompt-file prompt.txt --model-dir ~/Models/h3-apple-ref2va --resolution 768p --reference-resize match --duration 6 --seed 42 --output dialogue.mp4
```

```python
from h3_apple import generate

result = generate(
    prompt_file="prompt.txt", task="ref2va",
    reference_images=["character.png"], reference_audio=["voice.wav"],
    resolution="768p", reference_resize="match", duration=6, seed=42,
    model_dir="~/Models/h3-apple-ref2va", output="dialogue.mp4",
)
```

Supply 1–3 local audio files, each 2–15 seconds with one mono or stereo track.
WAV, MP3 and other formats decoded by the installed FFmpeg are accepted;
embedded cover art is allowed. Use the video argument for files containing
moving pictures. At most 12 image, video and standalone audio files can be
combined. Audio-only reference lists and FL2VA first/last anchors mixed with
Ref2VA references are rejected before model loading, following the
[LightX2V input contract](https://github.com/ModelTC/Minimax-H3-Turbo/blob/main/minimax_h3_ref2va_pipeline.py).

## Numbering and soundtrack selection

Explicit audio files are Audio 1, Audio 2, etc., in argument order. Enabled
video soundtracks follow them, in video order; a silent or disabled soundtrack
does not consume an Audio number. Picture and Video numbers are independent.
References are packed as images, standalone audio, then videos; this ordering
also affects the model's position encoding and is recorded for reproducibility.

By default, reference videos retain the existing behavior of contributing their
soundtracks. Add `--no-reference-video-audio` or `reference_video_audio=False`
to ignore all video soundtracks while retaining explicit audio files:

```bash
h3 generate --task ref2va --reference-video scene.mp4 --reference-audio voice.mp3 --no-reference-video-audio --prompt-file prompt.txt --model-dir ~/Models/h3-apple-ref2va --duration 6 --seed 42 --output scene-with-voice.mp4
```

The soundtrack switch requires a video reference. In the prompt, state what
Audio 1 should provide, such as voice timbre, delivery or musical style, and
write the intended new dialogue explicitly. See the
[MiniMax audio-reference guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/main/docs/VIDEO_PROMPT_WRITING_GUIDE_ref_en.md#24-audio-n).

## Processing and validation scope

Files are snapshotted and hashed before encoding. FFmpeg resamples to 32 kHz
stereo; mono is duplicated. Audio is limited to the padded model duration,
without looping short references. Run metadata records the actual sample
count, audio numbering, waveform/latent hashes and soundtrack selection.
The audio encoder uses posterior means and its native latent normalization.
Reference rows remain fixed during denoising; only generated rows are decoded.

Requests with independent audio default to 768p and Dense attention. The new
condition is not assumed compatible with transferred VSA gates. Image-only,
T2VA and FL2VA retain their existing VSA recipes.

Audio conditions the model's generated sound; it is not remuxed directly into
the output. File decoding, nonzero reference latents and successful generation
are separate from voice similarity, intelligibility and lip synchronization.
Do not interpret a completed MP4 as proof of those quality properties.
