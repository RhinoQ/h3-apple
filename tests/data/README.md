# Ref2VA geometry fixtures

`ref2va_layouts.json` records the fixed FastVideo source URL and SHA-256, inputs,
CPU dependency versions, and the digest of `ref2va_layouts.npz`. Expected arrays
come from that unmodified upstream module: call `build_ref2va_packed_sequence`
with each case and `(1, 2, 2)`, then `build_row_timesteps` for the recorded steps,
using `max(video_timestep, 0.999)` and `1.0` for the reference timesteps. Serialize
all returned layout fields and the timestep values/inverse arrays.

The reference runs on Python 3.12, whose float `sum` differs from Python 3.11.
The fixture includes ordered video references to expose that difference before
casting position coordinates to float32. These synthetic arrays check geometry;
they establish no trained encoder, inference performance, or media-quality claim.
