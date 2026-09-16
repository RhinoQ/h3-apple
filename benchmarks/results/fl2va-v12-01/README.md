# FL2VA LightX2V v1.2: first/last-frame integration check

One five-second 768p clip completed on an Apple M5 Max with 128 GiB unified
memory. The two supplied frames guide the same skater from the left side of a
graffiti wall to a crouched pose on the right. This case had been reserved
before generation; its prompt, endpoints and seed were not tuned on the output.

| Measurement | Observed value |
| --- | --- |
| Product implementation | `5a0d87f`, package `0.1.0.dev9` |
| Recipe | Native FL2VA + LightX2V four-step v1.2; Euler shifts 6/3; 50 transferred VSA gates |
| Delivery / model canvas | 1366×768 / 1376×768; 120 delivered / 124 model frames |
| Steps / sparse calls | 4 / 200, no Dense fallback |
| End-to-end time | 815.52 s (13 min 35.52 s), including diagnostics and complete media validation |
| Conditioning / denoising | 72.07 s / 653.11 s |
| Video / audio decode | 78.40 s / 0.51 s |
| Peak MLX allocation | 31.43 GiB; this is not total process or system memory |
| Host conditions | AC power, no swap; nominal thermal state at start, fair at finish |

All 120 decoded frames were reviewed in six labelled contact sheets, with
native-size checks at frames 0, 48, 68, 96 and 119. The visible person, clothing,
pads, skates, scene layout and endpoint compositions remained coherent. No
duplicate actor, severed limb, cut or added caption was observed at those review
scales. Fine face, hand and skate details remain soft; the 854×480 source
endpoints already contain motion blur. The last delivered pose is close to the
reference, not a pixel-identical copy of it.

This was a nonblind, frame-based review of one clip. Real-time motion naturalness
and audio quality have not been granted human acceptance in this record. Audio
delivery was checked for finite, non-silent stereo samples and complete timing.
There was no matched old-LoRA or Dense run, so this result establishes neither a
quality improvement nor a speedup. First-only, last-only and longer FL2VA clips
have structural tests but are not covered by this generation result.

## Reproduce

Prepare the separate [FL2VA v1.2 model bundle](../../../docs/fl2va.md). The
source is the pinned [rollerblade video](https://huggingface.co/datasets/emirkisa/DAVIS-2017-480p-mp4/resolve/06c7e6d99d6a7ddc7edbeaa6be838316feb70989/rollerblade_raw_24fps.mp4)
from a third-party DAVIS re-encode. Source SHA256:
`9e098d13dfce4ecb522fe4a2e13d479404913cec6867a1baa29144d1dae123a3`.
The media is not bundled here. Extract zero-based frames 0 and 34, preserving
their original pixels (the recorded extraction used FFmpeg 8.1.2):

```bash
ffmpeg -v error -n -i rollerblade_raw_24fps.mp4 -vf 'select=eq(n\,0)' -frames:v 1 first.png
ffmpeg -v error -n -i rollerblade_raw_24fps.mp4 -vf 'select=eq(n\,34)' -frames:v 1 last.png
```

First PNG SHA256: `4381f888c0113b10b2811d86b16f107294e8177fa20d78815c8f05ff87b469bc`.
Last PNG SHA256: `d4acd558b740d8d04da20a6bd24cac8d729b738e95296ba86469cf366e0c8853`.
Different PNG encoders can change file hashes without changing decoded pixels.

Save this complete prompt as `prompt.txt`:

> A five-second continuous photorealistic shot connecting the supplied first and last frames. The inline skater lands smoothly and glides a short distance, keeping both skates and protective pads. Preserve the same person, face, clothes, body proportions, background layout and camera viewpoint. Begin with the first-frame composition and end with the last-frame composition. Keep the full body visible as in the references, with coherent limbs and equipment; no close-up, zoom, cut, duplicate person, title or subtitle. Natural activity sounds and ambience without dialogue or music.

The exact recorded prompt has no trailing newline. With the fixed project
Conda environment activated, run:

```bash
h3 generate --task fl2va --prompt-file prompt.txt --first-frame first.png --last-frame last.png --model-dir ~/Models/h3-apple-fl2va-v12 --resolution 768p --duration 5 --seed 3301 --diagnostics --output skater.mp4
```

The output SHA256 was `f596f3e2cf5558628a9a696193f881da53d22428f5b1ab9dbe7c21f0846104f4`.
The installed runtime SHA256 was
`716fadc0f9dea19f2c716fa4c7140e91934d1c2a8cea9e76b5b5827243306c6b`;
backend library SHA256 was
`1876795e05b3434925e745fbf6e9f0c8c0446b666224c9d881609ab353e94e51`.
Use the matching MLX 0.32.0 build from the installer. Model conversion and seed
streams differ from CUDA/ComfyUI; cross-platform pixel identity is not promised.

The original external test harness incorrectly expected 200 progress messages.
The product intentionally reports every ten blocks: 20 messages for 200 calls.
This harness error was identified and its correction recorded before the video
completed. The original error was retained; an independent check verified the
completed output without rerunning generation or changing its quality criteria.

## Existing task compatibility

The unchanged T2VA amber-marble case and one-image Ref2VA portrait case were
rerun at five seconds / 576p against the stable `f35a34a` integration outputs.
Both delivered exactly the same decoded video pixels and stereo PCM samples.
All 29 saved Ref2VA arrays, including conditioning, all four sampling steps,
final latents and decoded content, were also identical. MP4 container bytes
changed with the exact movie-timescale fix; this was allowed before the runs.
Both used 4 NFE and 200 sparse calls without fallback. Exact prompts, seeds,
identities, observed times and checks are in [the compatibility record](unchanged-task-checks.json).
