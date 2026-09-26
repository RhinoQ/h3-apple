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

`tests/native_compute_plan.cc` checks replay legality against the built library:
valid and repeated plans, conflicting plans, invalid shapes/splits, and a plane
budget too small for the requested split. It loads native kernels but does not
load model weights or submit GEMMs. This tests the budget contract, not operation
on a small-memory computer. From the product checkout, after the native build:

```sh
c++ -std=c++20 -O2 -mmacosx-version-min=26.0 \
  -I.local/native-source -I.local/native-source/include -I.local/native-build-01 \
  tests/native_compute_plan.cc .local/native-build-01/libvpipe.0.dylib \
  -Wl,-rpath,"$PWD/.local/native-build-01" -o .local/native-compute-plan-test
.local/native-compute-plan-test
```
