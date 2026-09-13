# Reproduce a video study

Every case provides the input order, original media URLs, SHA-256 hashes,
generation parameters, source commit, and a runnable command. Run one generation
at a time on the tested M5 Max / 128 GiB configuration. See the runtime's
[hardware and storage requirements](https://github.com/RhinoQ/h3-apple/tree/40572ed48fa1904178453214b3afe7032e48b860#hardware-and-memory).

## 1. Install the build shown under the video

Use a working folder of your choice. The commands on the page are relative to
that folder. Install ARM64 Conda/Miniforge first. Each checkout's installer uses
its own Conda environment and pinned dependencies.

For cases marked **0.1.0.dev2**:

```bash
git clone --branch codex/guide-inputs https://github.com/RhinoQ/h3-apple.git h3-apple-dev2
git -C h3-apple-dev2 checkout --detach f35a34ad06df0ba3f9403c317e853fdf3383ad0e
./h3-apple-dev2/install.sh --ref2va
```

For cases marked **0.1.0.dev3+guide2**:

```bash
git clone --branch codex/guide-inputs https://github.com/RhinoQ/h3-apple.git h3-apple-guide2
git -C h3-apple-guide2 checkout --detach 40572ed48fa1904178453214b3afe7032e48b860
./h3-apple-guide2/install.sh --ref2va
```

Install each build only once and reuse it for all matching cases. The guide2
build contains experimental video/audio references, portrait output and
first/last-frame input support. The latest tagged release predates these
interfaces. The per-case Python API call is the supported entry point for them;
the older CLI does not expose all of their arguments.

## 2. Prepare the matching model once

Model downloads are separate from the small case-input downloads. Starting from
an empty cache requires substantial storage and bandwidth: the text recipe alone
contains about 139 GiB of source files. Reuse existing pinned snapshots where
possible. Review model terms and the download plan before starting.

| Task | Base and encoders | Four-step weights | Attention | Default local bundle |
| --- | --- | --- | --- | --- |
| T2VA | [MiniMax H3 FL2VA, pinned revision](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/FL2VA) through the standard text conversion recipe | [FastH3 VSA Data-Free adapter, pinned revision](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-LoRA/tree/bcf40ca6f457ed66f8badf13514943e390205fca/vsa-datafree), including its T2VA deltas | VSA | `~/Models/h3-apple-t2va` |
| Ref2VA | [MiniMax H3 Ref2VA transformer and reference encoders](https://huggingface.co/MiniMaxAI/MiniMax-H3/tree/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/Ref2VA); output components from the text bundle | [LightX2V Ref2V four-step v0.1 BF16](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/ec01fa4c86263832faa0bd1d6d8f36a281eaabb2/minimax_h3_ref2v_turbo_4step_v0.1_bf16.safetensors), rank 128 / alpha 8; only the 50 compression gates from the pinned FastH3 adapter | VSA | `~/Models/h3-apple-ref2va` |
| FL2VA | Native FL2VA transformer from the pinned H3 revision; this collection uses the Ref2VA processor, tokenizer, Qwen and video VAE for reference encoding, plus the text bundle's output components | [LightX2V FL2V four-step v0.1](https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/minimax_h3_fl2v_turbo_4step_v0.1.safetensors), SHA-256 `5ff4a12c8b4599fec716e1b15a45e504e0d1129111896bdcde5ac4a15e395b29`, rank 128 / alpha 8 | Dense, shifts 12 / 3; retained FastH3 gates are unused | `~/Models/h3-apple-fl2va` |

All three use INT8/group64 with BF16 arithmetic. Their portable content
manifests are [T2VA](models/t2va.json), [Ref2VA](models/ref2va.json), and
[FL2VA](models/fl2va.json). They contain file hashes, not model weights.

Prepare the text bundle with the standard downloader; `--plan` does not download:

```bash
./h3-apple-dev2/.local/envs/h3/bin/h3 models prepare --model-dir "$HOME/Models/h3-apple-t2va" --plan
# Run only after reviewing the plan and model terms:
./h3-apple-dev2/.local/envs/h3/bin/h3 models prepare --model-dir "$HOME/Models/h3-apple-t2va" --allow-large-download
```

Ref2VA preparation is documented in the pinned
[reference-model guide](https://github.com/RhinoQ/h3-apple/blob/f35a34ad06df0ba3f9403c317e853fdf3383ad0e/docs/ref2va.md#installation-and-models).
Use the native `Ref2VA/transformer`, the pinned Ref2V adapter, and the text bundle's
`components` folder. The native reference directory must include `processor`,
`tokenizer`, all fourteen Qwen `text_encoder` shards, and `video_vae/source`.

For FL2VA, use the same conversion API with `task="fl2va"`, the **FL2VA** native
transformer, and the **FL2V** adapter. Obtain the linked official files and point
the paths below at them. Do not use the Ref2V adapter or FastH3 T2VA deltas.
The required native components are available in the pinned MiniMax snapshot.
This preparation command performs no downloads:

```bash
MLX_ENABLE_TF32=0 MLX_METAL_GPU_ARCH=applegpu_g16s \
./h3-apple-guide2/.local/envs/h3/bin/python - <<'PY'
from pathlib import Path
from h3_apple.conversion import convert_dit
from h3_apple.assets import import_assets
from h3_apple.host import device_lock
from h3_apple.io import digest

native = Path("h3-sources/native")  # Contains the pinned FL2VA and Ref2VA directories.
adapter = Path("h3-sources/minimax_h3_fl2v_turbo_4step_v0.1.safetensors")
gates = Path("h3-sources/vsa-datafree/adapter_model.safetensors")
checkpoint = Path("h3-fl2va-checkpoint")  # Must be a new directory.
assert digest(adapter) == "5ff4a12c8b4599fec716e1b15a45e504e0d1129111896bdcde5ac4a15e395b29"
assert digest(gates) == "42dc502a2078f166c396a1fa75f29728d1844363652d345d5ef3e2b444ed6470"
with device_lock():
    import mlx.core as mx
    mx.set_memory_limit(60 * 1024**3)
    mx.set_cache_limit(2 * 1024**3)
    convert_dit(native / "FL2VA/transformer", adapter, checkpoint,
                print, task="fl2va", gate_source=gates)
import_assets(checkpoint, Path.home() / "Models/h3-apple-t2va/components",
              Path.home() / "Models/h3-apple-fl2va",
              fl2va_native=native / "Ref2VA")
PY
```

The generation command must not inherit the conversion-only architecture
override. It is scoped to the one command above. Local source paths change the
bundle's provenance identity, so the reproduction script compares all portable
file hashes and recipe fields instead of requiring the original machine's bundle
ID. It rejects a model mismatch before generation. Preparation is qualified by
existing on-device conversions; this guide does not claim a new clean-machine,
full-download installation test.

## 3. Fetch the case inputs and generate

Copy the command below the selected video. It fetches `reproduce.py`, the
case's exact prompt from its public record, the ordered reference files and the
model content manifest. It checks every prompt/reference hash and writes
`case-NN/prompt.txt`, reference files, `case.json`, and `model.json`.

The script preserves the exact paragraph joining used by this collection and
checks the prompt and media against their recorded hashes. The published prompt
stays pinned even if the source article later changes. You can also supply a
saved source page with `inputs --guide-html guide.html`,
or the original prompt with `inputs --prompt-file prompt.txt`. Each must still
match the recorded hash. Existing files with different content are never replaced.

The full text used by each local request is displayed below its video with a
copy button and source attribution. The run command reads the same text from
the downloaded `prompt.txt` automatically. No file upload or selection is needed.

Before spending GPU time, add `--check-only` to the `run` command. It checks the
installed source identity, prepared model manifest, input bytes and resolved API
request without generating a video. Remove the flag to generate with a progress
bar. Choose a new `--output` path for every rerun; the runtime preserves old runs.

All case records retain the original source geometry and local delivery geometry.
The collection uses four steps, seed 42 and 576p. Case 1 preserves page image order
(architecture, person, flag, close-up), despite the prompt's inconsistent labels.
Case 15 uses the three supplied images and lacks the unpublished reference video.
Case 27 uses the runtime's minimum five-second delivery. These are disclosed
differences. A fixed recipe makes a run inspectable; it does not guarantee
bit-identical output across different hardware or backend builds.
