# Model preparation

This page describes the text-generation bundle. For ordered reference images,
use the dedicated [Ref2VA weights and import instructions](ref2va.md).

Read the [MiniMax-H3 model terms](../licenses/MiniMax-H3.txt) before preparing
weights. The code's Apache-2.0 license does not change the model's geographic,
use, or distribution conditions. The pinned official agreement excludes the
United States, European Union, United Kingdom, and South Korea and specifies
distribution and commercial-use conditions. Uses outside that grant require
separate authorization. The [pinned official agreement](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/LICENSE)
is the source of those conditions. Weights are not included in Git or the
Python wheel.

## First preparation

```bash
h3 models prepare --plan
h3 models prepare
```

`--plan` validates reusable files and shows each source, deduplicated missing
bytes, and additional space required on the cache and destination volumes.
It does not download models. The pinned source list uses the public MiniMax
FL2VA partition and official FastH3 VSA adapter, without Ref2VA or unrelated models.

See the [measured disk-space budget](../README.md#disk-space) for first setup,
the retained generation bundle, environment size and free space needed when
generating. Components share files with the source cache on the same volume;
different filesystems require real copies. Use the local `--plan` for the
actual storage increment on each volume.

Downloads exceeding 20 GB stop before transfer. After reviewing the plan,
explicitly allow them with:

```bash
h3 models prepare --allow-large-download
```

Downloads are pinned by revision, length, and SHA256. Resume requests retrieve
only missing bytes. The source cache defaults to `~/Models/.h3-apple-sources`
and the generation bundle to `~/Models/h3-apple`. Use `--cache-dir` and
`--model-dir` to select another volume; `H3_MODEL_DIR` sets the everyday default.
Conversion runs in a separate worker and atomically publishes the completed bundle.

## Reuse existing downloads or converted weights

Repeat `--reuse-dir` for existing official files. Repository snapshot roots,
FL2VA directories, adapter snapshots, and standard Hugging Face caches are supported:

```bash
h3 models prepare --reuse-dir /path/to/MiniMax-H3/FL2VA --reuse-dir /path/to/FastH3-LoRA --plan
h3 models prepare --reuse-dir /path/to/MiniMax-H3/FL2VA --reuse-dir /path/to/FastH3-LoRA
```

Every reused file receives a full SHA256 check; matching names are insufficient.
Files on the same filesystem use hard links. Cross-volume copies are verified
again. Removing an old source filename does not remove the new bundle's link,
but editing either name changes shared content. Treat prepared assets as read-only.

A matching MLX FastH3 VSA INT8/group64 checkpoint and complete components can
also be imported directly:

```bash
h3 models prepare --checkpoint /path/to/dit --components /path/to/components --model-dir /path/to/new-bundle
```

The components directory must contain `text_encoder/`, `tokenizer/`, `vae/`,
and `audio_vae/`. Import records actual content identity. Missing converter
provenance is marked unknown; it does not imply equivalence to an official
full student snapshot.

## Verification and recovery

```bash
h3 models status
h3 models verify
```

`status` checks manifest identity, sizes, and modification times. `verify`
additionally hashes every file. Running `prepare` again recognizes a completed
bundle and returns without reconversion. Existing bundles are never overwritten.
For a new model or converter, prepare a new directory, verify it, and then
switch `H3_MODEL_DIR`.

Interrupted downloads retain `.partial` files with SHA256 records. Retries
resume them. A server ignoring Range requests, corruption, or changed length
produces an explicit error instead of silently downloading everything again.
Retain or move the problem file, then inspect `--plan` again. Failed conversions
keep their unique work directory and logs. Successful conversions remove their
own temporary outputs and retain the plan and conversion receipts.

## Version and conversion identity

The pinned file list is [model-sources.json](../src/h3_apple/data/model-sources.json).
Bundle v2 binds content, source revisions, adapter, converter source, precision,
quantization, schedule caches, and backend settings. Existing v1 content
manifests remain readable.
Ref2VA imports use bundle v3, additionally binding the task and component paths
to the identity and including the native reference encoders and conversion recipe.

This build merges the official rank-64 VSA adapter into native MiniMax
parameters, computes AdaLN tables for the four-step schedule, and saves an
affine INT8/group64 DiT with the full FP32 VideoVAE. This does not establish
byte-for-byte equivalence to a full student snapshot.

Conversion selects MLX's `applegpu_g16s` architecture to reproduce the validated
pre-NAX cache rounding on the physical M5. Generation restores the actual GPU
architecture and uses M5 NAX acceleration. A second MLX installation is unnecessary.
See the reproduction evidence in [validation](validation.md).
