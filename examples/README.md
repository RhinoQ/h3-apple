# Generated videos

The [README gallery](../README.md#video-comparisons) presents every completed
Ours/vpipe comparison in the four current benchmark rounds: **14 pairs, 28
native videos**, comprising ten five-second and four fifteen-second pairs.

Each synchronized preview puts Ours on the left and vpipe / VDN on the right,
with generation time written above each panel. Both run at their original
24 fps for the complete duration. Panels are resized to 640×360 for display;
the timing and quality reference is the original 1366×768 video.
**Preview audio is Ours.** Open each original to review its own 32 kHz stereo track.

[Download all native videos](https://github.com/RhinoQ/h3-apple/releases/tag/benchmark-videos-2026-09-11)
or use the individual links in the gallery.
The [gallery manifest](gallery/manifest.json) binds public URLs, elapsed times,
original/preview/poster hashes, fixed source results, and the display conversion.
Posters use the first frame; no output or frame was selected for visual quality.
The original eight videos received [human acceptance](../benchmarks/reviews/existing-eight-20260911.json);
the twenty additional videos await human quality review.

## Original compact examples

These earlier Ours-only previews come from
[native-three-02](../benchmarks/results/native-three-02/README.md). They retain
all fifteen seconds and audio at 640×360. Their resolution does not describe
native generation quality or workload. [Preview provenance](previews/manifest.json)
records original and derivative hashes.

### Motion graphics / seed 2026

[Play the fifteen-second preview](previews/motion-graphics-ours.mp4) ·
[Full prompt](../benchmarks/prompts/motion-graphics.txt)

[![Motion graphics at fixed intervals](previews/motion-graphics-ours.jpg)](previews/motion-graphics-ours.mp4)

### Bakery / seed 87001

[Play the fifteen-second preview](previews/bakery-ours.mp4) ·
[Full prompt](../benchmarks/prompts/bakery.txt)

[![Bakery at fixed intervals](previews/bakery-ours.jpg)](previews/bakery-ours.mp4)

The three-second contact-sheet intervals were fixed, without manual frame
selection. The vpipe sheets are [motion graphics](previews/motion-graphics-vpipe.jpg)
and [bakery](previews/bakery-vpipe.jpg). Raw experimental files remain preserved.

## Generate your own

From the product repository, with a prepared Ours environment:

```bash
"$PWD/.local/envs/h3/bin/python" -m h3_apple generate --prompt-file benchmarks/prompts/motion-graphics.txt --seed 2026 --output motion-graphics.mp4
"$PWD/.local/envs/h3/bin/python" -m h3_apple generate --prompt-file benchmarks/prompts/bakery.txt --seed 87001 --output bakery.mp4
```

The benchmark prompts remain byte-for-byte unchanged. The interface generates
audiovisual video from text without a reference image. Exact shot execution and
accurate rendered text are not guaranteed. See [generate.py](generate.py) for a
Python example with arbitrary prompts.
