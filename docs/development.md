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

## Software releases

Update both `version` in `pyproject.toml` and `__version__` in
`src/h3_apple/__init__.py`. Use `0.2.1` in these files; the CLI reads
`__version__`, while Git tags use the `v` prefix (`v0.2.1`). Update current-version
documentation and retain the original version in historical benchmark records.
Rebuild and install a regular wheel so package metadata, Python imports and
`h3 --version` agree; editing the checkout alone does not update an installed
environment. Keep model recipe and bundle-format versions unchanged unless
those formats or recipes actually change.

Use patch versions for compatible fixes (for example, `0.2.1`) and minor
versions for feature milestones (for example, `0.3.0`). A version change
does not establish new quality or performance results. A local commit or tag
does not publish a GitHub release; keep published installation links pinned to
available assets until the new release is uploaded and verified.

[Software releases](https://github.com/RhinoQ/h3-apple/releases) use annotated
`v<package-version>` tags. The tag, `pyproject.toml`, and `h3 --version` must agree.
Development versions are marked **Pre-release** on GitHub. Installation examples
pin the published tag so a later change on `main` does not change that release.

Build the wheel and complete source archive from the tagged commit. Verify a
regular wheel installation outside the checkout, run the relevant tests, and
check that all packaged runtime files match the validated baseline. Publish
the source archive, wheel, `release-manifest.json`, and `SHA256SUMS` together;
the manifest records the commit, runtime identity, environment locks, and
artifact hashes. Verify the published downloads before announcing the release.
Keep published tags and artifacts unchanged; corrections use a new version.
Video-only releases have separate `benchmark-videos-*` tags.
