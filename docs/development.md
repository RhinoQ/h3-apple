# From research to a stable release

The stable generation core lives in this repository. The research repository,
`tqlm-h3-apple`, retains proposals, comparison designs, ablations, blind reviews,
and raw results. Historical P001–P100 archives remain unchanged. New research
calls a pinned product version; everyday generation does not read research files.

Before the first publication to [RhinoQ/h3-apple](https://github.com/RhinoQ/h3-apple),
the maintainer requested that the authors and committers of fifteen local
commits become RhinoQ. File contents, messages, and timestamps were unchanged.
The [commit map](evidence/github-author-map.json) records identical Git trees.
Existing experiments retain the commit IDs actually run; use the map to locate
their public source. This attribution change creates no new experimental result.
The research baseline separately points to the published commit.

## Development and validation

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

Hardware validation calls the public CLI/API from outside the repository with
a fixed interpreter, model identity, full input, and preset. Declare the question,
single change, acceptance criteria, and stopping conditions before running.
Preserve raw results in a unique directory. `diagnostics=True` exports necessary
tensors through the existing observer; ordinary runs do not prepare diagnostics.

## Adopting a proposal

1. Pin the stable product commit, wheel/source SHA, environment lock, model identity, and preset.
2. Create `codex/pNNN-description` in the product repository and change the actual core. Keep ablations, quality decisions, and rejected candidates in research.
3. Prepare separate fixed Conda environments with regular wheels for the stable version and candidate. Reuse models only by verified identity.
4. Select the frozen installations through the research baseline and launcher, then call the public CLI. Public benchmark prompts are already seen; tune only on calibration data and use independent held-out data for new generalization claims.
5. After the predeclared speed and quality gates pass, merge the product branch, add relevant regression coverage, and verify full timings after integration. Update only the recipe, model/calibration assets, or environment locks that actually changed.
6. Publish a summary linked to fixed evidence and limitations. Update the research baseline commit. Preserve the previous wheel, locks, and model identity for explicit rollback.

For an extraction or port, first verify step outputs and full audiovisual
delivery. Approximate acceleration is allowed only with predeclared acceptance
gates. Identical seeds need not create identical noise across engines. A system
comparison and an incremental ablation support different conclusions. Pin new
upstream versions and avoid claiming adopted upstream gains as new local gains.

No Git submodule, third shared-core repository, or bidirectional directory
synchronization is needed. Use Ours/vpipe when establishing or updating the
public external comparison; everyday proposals compare the candidate with
the stable product.

## Upstream code and distribution

Required FastVideo MLX files are bundled as a fixed snapshot. Paths and local
changes are recorded in [sources.json](sources.json). Review actual diffs,
licenses, and runtime results when updating. Official FastH3 is outside the
current comparison scope.

Our Apache-2.0 code, upstream MIT/BSD/Apache code, and separate model terms are
attributed in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES) and the wheel's license
files.

Review the complete code, evidence, and presentation before publication.
Large originals belong in Release assets; small previews and input/run manifests
with hashes belong in Git. Public download links must resolve to published files.
The [gallery manifest](../examples/gallery/manifest.json) maps each displayed
comparison to its source results and native videos.

The English edition translates presentation text without changing measurements.
[Translation provenance](evidence/english-edition.json) preserves the source
commit and hashes for translated JSON records. Historical plan hashes continue
to identify their original snapshots.
