# Development

See [architecture](architecture.md) for the runtime layout and [validation](validation.md)
for completed checks and their scope.

## Install and test

```bash
./install.sh
"$PWD/.local/envs/h3/bin/python" -m pip install -r environments/dev.lock
"$PWD/.local/envs/h3/bin/python" -m pytest -q
```

Fast tests use temporary files and small media, without loading H3 or relying
on local historical experiments. Installation-independence tests require a
regular wheel installation first. After code changes, rerun `./install.sh`.
Formal timing uses a frozen, regular installation. Editable installs are useful
during development but do not qualify as frozen-release measurements.

## Validate performance changes

Run the public CLI/API from outside the repository with a fixed interpreter,
model identity, full input, and preset. Declare the question,
single change, acceptance criteria, and stopping conditions before running.
Preserve raw results in a unique directory. `diagnostics=True` exports necessary
tensors through the existing observer; ordinary runs do not prepare diagnostics.

Compare a candidate with a fixed stable version using separate regular wheel
installations. Match inputs, models, delivery specifications, and measurement
conditions except for the declared change. Record full audiovisual delivery
time and quality findings, including failures. Public benchmark prompts are
already seen; use separate calibration and held-out data for new quality claims.
Identical seeds need not create identical noise across engines.

Add regression coverage appropriate to the change and verify timings after
integration. Keep the previous wheel, environment locks, and model identity
available for rollback. The optional [Ours/vpipe benchmark](../benchmarks/README.md)
compares complete systems with different recipes; it does not isolate an
individual optimization's contribution.

## Upstream code and distribution

Required FastVideo MLX files are bundled as a fixed snapshot. Paths and local
changes are recorded in [sources.json](sources.json). Review actual diffs,
licenses, and runtime results when updating.

Our Apache-2.0 code, upstream MIT/BSD/Apache code, and separate model terms are
attributed in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES) and the wheel's license
files.

Review the complete code, evidence, and presentation before publication.
Large originals belong in Release assets; small previews and input/run manifests
with hashes belong in Git. Public download links must resolve to published files.
The [gallery manifest](../examples/gallery/manifest.json) maps each displayed
comparison to its source results and native videos.
