# Ultrafast generation with native vpipe

Version 0.3.0 adds `ultrafast`: native INT8 GEMM + Sol-Attn + SageAttention,
with four denoising steps. Select it explicitly with `--preset ultrafast`;
`ours` remains the default. Speed and quality depend on the input and hardware.
[Release validation and limits](validation.md#v030-ultrafast).

H3 Apple invokes the separately installed **vpipe inference core**. It handles
input snapshots, process cancellation, resource monitoring and final MP4
validation. No second copy of the vpipe Metal kernels is maintained here.

## Installation and registration

Use an existing [vpipe installation](https://github.com/tgo-app-dev/vpipe) and
its native **8-bit, group-64, unmerged** MiniMax-H3 model. The tested CLI/graph
interface is commit `f34e2cc3a3adae759eea254419f436f5b7800057`.
Other versions need separate validation. See the upstream
[H3 preparation guide](https://github.com/tgo-app-dev/vpipe/blob/f34e2cc3a3adae759eea254419f436f5b7800057/docs/MINIMAX-H3.md).
The converted MLX bundles used by `ours` are not native vpipe checkpoints.

Register a FL2VA model for both text and keyframe generation:

```bash
h3 models import-vpipe \
  --model-dir "$HOME/Models/h3-native-fl2va" \
  --native-model /path/to/MiniMax-H3-FL2VA-8bit \
  --lora /path/to/minimax_h3_fl2v_turbo_4step_v1.2_768p_bf16.safetensors \
  --vpipe-binary /path/to/vpipe/build/apps/vpipe/vpipe \
  --vpipe-library /path/to/vpipe/build/libvpipe.0.1.dylib
```

For image Ref2VA, register its native Ref2VA model in a separate bundle with
the pinned [DARE/TIES fro0995 adapter](ref2va.md). Registration verifies the
adapter checksum and model partition, hashes existing files and writes a small
`vpipe.json` manifest. It downloads and copies no model weights. Keep those
files in place. Changed binaries or assets require a new registration.

```bash
h3 doctor --preset ultrafast --model-dir "$HOME/Models/h3-native-fl2va"
h3 models verify --model-dir "$HOME/Models/h3-native-fl2va"
h3 generate --preset ultrafast --model-dir "$HOME/Models/h3-native-fl2va" \
  --prompt-file prompt.txt --resolution 576p --duration 5 --seed 0
```

Use `--first-frame` / `--last-frame` with the FL2VA bundle, or ordered
`--reference-image` arguments with the Ref2VA bundle. `--reference-resize match`
uses the output canvas area for each reference image, as in `ours`.
The Python API uses the same `preset` and `model_dir` arguments.

## Scope and reproducibility

- Supported: T2VA, still-image Ref2VA, first/last-frame FL2VA, landscape and
  portrait, existing 576p/768p delivery sizes and 5–15 second durations.
  Reference video/audio is rejected by ultrafast; use `ours` for it.
- Ultrafast uses four actual denoising steps. The native graph has
  five sigma entries including terminal zero. FL2VA/T2VA use LightX2V v1.2
  with video/audio shifts 6/3; Ref2VA uses DARE/TIES with shifts 12/3.
- Native seeds use vpipe's RNG. The same integer seed does **not** produce
  identical initial noise or frames across vpipe and MLX. Encoders, VAE
  sampling and weight treatment also differ. A whole-preset comparison is
  not an isolated attention experiment.
- The run record contains the full native graph, actual binary/library
  hashes, asset identity, reference snapshots, recipe and acceleration log
  confirmations. An unconfirmed four-step run or a detected Sol/Sage fallback
  fails instead of being reported as a successful ultrafast run.
- Ctrl-C, callback cancellation and timeout stop the entire worker process
  group. Existing output files are never overwritten. Failures preserve the
  workspace; `--diagnostics` retains the native log and graph on success too.
- The common delivery adapter validates the native streams, center-crops the
  model canvas and trims by delivery frame/audio sample counts. It uses a
  shared video/audio MP4 timescale so fractional-second endpoints stay aligned.

## Memory

This integration retains H3 Apple's existing M5/macOS/memory checks. It has
**not** certified 16 or 24 GB machines. The vpipe upstream 16 GB result uses
streamed weights and phase unloading; available memory can instead be used to
retain transformer blocks and avoid repeated SSD reads. Its small example
does not establish that all longer or multi-reference workloads fit in 16 GB.
See the upstream [memory explanation](https://github.com/tgo-app-dev/vpipe/blob/f34e2cc3a3adae759eea254419f436f5b7800057/docs/MINIMAX-H3.md#memory).

Process RSS, Metal allocator peaks and vpipe's predicted working sets are
different measurements. Compare identical workloads and metrics before using
any of them as a product hardware requirement.
