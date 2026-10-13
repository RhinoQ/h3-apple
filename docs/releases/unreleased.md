# Unreleased — Choose the backend independently of quality

Fast and medium both accept VSA or SOL and default to VSA. Quality controls
sampling resolution and decoding; `mode` selects the generation backend.

| Quality | Default backend | Optional backend | Output pipeline |
| --- | --- | --- | --- |
| Fast | VSA | SOL | 544p + X2 |
| Medium | VSA | SOL | Native 768p |
| High | VSA models with Dense attention | — | Native 768p + VOSR |

```sh
h3 generate --image reference.jpg --prompt-file scene.txt --quality fast
h3 generate --image reference.jpg --prompt-file scene.txt --quality medium --mode SOL
```

Python uses the same settings: `generate(..., quality="fast", mode="SOL")` or
`generate(..., quality="medium", mode="VSA")`. Fast and medium still support
5–15 seconds at whole 24 fps frames. High remains fixed at five seconds.

## Existing calls

Calls that omit `mode`, including generation without a named quality and the
`--upscale` shortcut, now use VSA. Set `--mode SOL` or `mode="SOL"` explicitly
to keep SOL. Preparation, doctor and verification also default to VSA; use the
same explicit mode throughout setup and generation.

The backends need different prepared model bundles. Existing compatible models
are reused; pending downloads still require consent above 20 GB. No inference
kernel, weights, decoder or restoration recipe changes in this update. Equal
seeds across backends do not imply equal videos or improved task quality.

These changes are in the current source and are not part of published 0.8.2.
[Source installation](../development.md#verify-a-change) ·
[Advanced settings and measured performance](../advanced.md) · [Python API](../api.md).
