# Official FastH3 duration-alignment fix

FastVideo `a943220c115228ade5d57b3bab9a6a87fd600a10` divides the aligned frame
count by 24 and compares it with fifteen seconds. H3 requires a `17n+5` temporal
grid, so 360 frames align to 362. A valid fifteen-second target was therefore
rejected at initial or repeated validation.

The [patch](fastvideo-h3-frame-limit.patch) applies the same alignment to the
request and both duration bounds. It accepts valid model grids from 124 through
362 frames and continues to reject requests outside that range. Only entry
geometry validation changes; weights, attention, steps, precision, decoding,
and delivery cropping are unchanged. The 362 frames describe model work.
The comparison still strictly delivers 360 frames and fifteen seconds of audio.

## Apply and install

Create a local branch at the pinned upstream version, apply the patch, and
install normally. Adjust paths for your machine:

```bash
git -C /path/to/FastVideo switch -c codex/h3-frame-limit a943220c115228ade5d57b3bab9a6a87fd600a10
git -C /path/to/FastVideo apply --check /path/to/h3-apple/benchmarks/patches/fastvideo-h3-frame-limit.patch
git -C /path/to/FastVideo apply /path/to/h3-apple/benchmarks/patches/fastvideo-h3-frame-limit.patch
git -C /path/to/FastVideo add fastvideo/mlx_runtime/minimax_h3_pipeline.py tests/test_mlx_h3_geometry.py
git -C /path/to/FastVideo commit -m "Fix H3 aligned duration limits"
/path/to/fastvideo-env/bin/python -m pip install --force-reinstall --no-deps --no-build-isolation /path/to/FastVideo
/path/to/fastvideo-env/bin/python -I -m pytest -q /path/to/FastVideo/tests/test_mlx_h3_geometry.py
```

When reproducing this historical experiment, start with its frozen configuration,
record the new local commit in `local.json`, retain the patch SHA in
`local_patches`, and update the installed `minimax_h3_pipeline.py` SHA256.
Use the label **Official FastH3 / VSA + frame-limit fix**. The local patch commit
was `17825c79c4d839d03f3907769f6b19cc982ca5d4`; a new local commit may have a
different hash. Current suites and `local.example.json` contain only Ours/vpipe.

## Validation and limits

The [validation record](fastvideo-h3-frame-limit.validation.json) binds the patch,
runtime files, wheel, and raw results. The original regular installation produced
**6 failures and 26 passes**. The patched regular installation passed **all 32
tests** and upstream pre-commit checks. Tests cover 360/362 frames, repeated
validation of aligned shapes, existing legal inputs, out-of-range rejection,
and internal short-sequence mode.

Both full public prompts reached
`output=1376x768x362 model=1376x768x362 audio_frames=362` through the real official
CLI. They were immediately canceled; processes ended and no MP4 was published.
This validates entry acceptance, not complete generation or performance.

The two original failures in [native-three-02](../results/native-three-02/README.md)
remain unchanged. Both later [full follow-up attempts](../results/fastvideo-frame-limit-01/README.md)
generated raw videos but failed delivery-duration validation and showed damaged
late frames. They produced no successful delivery timing. Entry correctness and
full generation results are recorded separately. Future attempts need new
directories and the explicit patched label. Ours' everyday runtime was unchanged.
