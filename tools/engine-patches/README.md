# Native compute policy

`stable-compute.patch` applies to the vpipe revision pinned before this change,
`f34e2cc3a3adae759eea254419f436f5b7800057`. It adds checked H3 QMM replay,
deterministic VAE shape selection, actual dispatch records and strict allocation
failure handling. It does not change Metal kernels, weights or attention math.

Apply it before following the native build instructions in `docs/development.md`.
The wrapper supplies the versioned policy internally and records it for every
generation, including when diagnostics are disabled. The current candidate
policy targets the 40-core M5 Max; qualification on other GPUs is separate.

Upstream behavior is retained when no product policy is supplied, for controlled
comparisons. Internal native environment controls are not public user settings.
