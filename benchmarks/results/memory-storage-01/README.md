# Memory and storage validation

This report measures complete generation and model preparation on an Apple M5
Max with 128 GiB of physical unified memory, running macOS 26.6.1. The main
question is which workloads finish when only a 64 GiB total memory budget
remains for macOS, other applications and H3 together.

## Outcomes

The current entry admits 768p / 5 seconds and 576p / 5–15 seconds from 64 GiB,
and longer 768p requests from 96 GiB. These are software admission boundaries
supported by the tested workloads, not an exact minimum or physical 64 GB
hardware certification. The integrated ordinary wheel passed 88 tests and
`pip check`, then completed the 96 GiB / 768p long-video run.

| Attempt | Total budget | Result | Observed seconds | Process-tree peak |
| --- | ---: | --- | ---: | ---: |
| Original policy · 768p / 5s | 64 GiB | Stopped: memory pressure | 91.06 | 33.03 GiB |
| 48 GiB residency, no cache · 768p / 5s | 64 GiB | Passed | 588.96 | 31.43 GiB |
| 48 GiB residency, original cache · motion / 768p / 5s | 64 GiB | Passed | 457.34 | 35.13 GiB |
| Same policy · bakery / 768p / 5s | 64 GiB | Passed | 455.39 | 34.41 GiB |
| Same policy · motion / 768p / 15s | 64 GiB | Stopped: swap growth | 446.63 | 46.83 GiB |
| Same policy · motion / 576p / 15s | 64 GiB | Passed | 1021.66 | 40.95 GiB |
| Unchanged converter · full model preparation | 64 GiB | Passed | 106.19 (monitor) | 31.18 GiB |
| Integrated entry · motion / 768p / 15s | 96 GiB | Passed | 2108.96 | 56.27 GiB |

Every completed attempt had normal memory pressure and zero swap growth.
The original short attempt stopped on sustained warning pressure. The 64 GiB
768p long attempt stopped after swap grew by 287,571,968 bytes; its MP4 was
not completed. Both failures are retained in the measurements.

All three current-policy videos with a matching prior prompt, seed and output
geometry (the two 768p short videos and the 96 GiB 768p long video) have identical MP4 hashes
to the original Ours outputs. The new 576p long video passed complete AV
validation; no new human quality acceptance is claimed.

## Model preparation and disk sizing

The complete public preparation command rebuilt the model from the fully
hashed local source cache under a 64 GiB total budget in 106.19 seconds.
The conversion subprocess took 17.15 seconds; the complete command also
includes source hashing and final import. No model files were downloaded.
All 35 payload files matched the existing reference sizes and SHA256 values.
The new bundle identity differs because its converter provenance records the
new installed source identity; model content is unchanged.

The sampled peak of source cache plus preparation files was 170.11574 GiB of
unique logical file bytes. Hard links were counted once. The completed cache
and bundle occupy about 170.13 GiB in allocated file blocks; the bundle alone
contains 93.71 GiB of unique logical payload and metadata. The measured Conda
environment plus private package cache uses about 1.67 GiB of allocated blocks.
Existing APFS clone sharing is not assumed for a new installation.

The largest sampled generation-directory footprint, including this test's
monitor logs, was 23.89 MiB with diagnostics disabled. The worker nevertheless
requires 20 GiB free throughout a run; this is operational headroom, not a claim
that every video consumes 20 GiB. Source downloads from an empty cache are
139.11 GiB of pinned files; their full network transfer was not repeated.

The [README disk budget](../../../README.md#disk-space) rounds these observations
up for setup and daily use. Different volumes need additional copies; use
`models prepare --plan` to inspect each destination. Removing the optional
source-cache names after verification leaves the prepared bundle's hard links
intact. Keep assets read-only and retain the bundle used for generation.

## Method and limits

The [measurement script](../../measure_resources.py) allocates, touches and
locks the excess physical pages with `mlock`. Every sample verifies that the
reservation remains wired. It releases its reservation when the command
finishes or a stop condition occurs. It changes neither `hw.memsize` nor
Metal's device memory limits. A 64 GiB test on this host reserves 64 GiB; a 96 GiB
test reserves 32 GiB.

Each generation starts a fresh public CLI process, uses the same prepared
model and four-step recipe, and ends only after complete video/audio decoding
and delivery validation. Prompts and seeds are the previously seen motion
graphics and bakery inputs. OS caches are retained, and background application
memory can change between runs. These are single resource observations, not
a controlled speedup estimate or a held-out quality evaluation.

The controller samples the complete H3 process tree with macOS
`proc_pid_rusage`, system VM page counts, memory pressure, swap and watched
files approximately every half-second. Process footprint, MLX phase counters,
and installed RAM are distinct measurements. The process-tree peak excludes
the reservation and other apps; it is not the minimum capacity of a Mac.
Short-lived peaks between samples may be missed; individual process lifetime
peaks are also recorded. Phase peaks run sequentially and must not be summed.

The resource test stops on critical pressure, warning pressure lasting two
seconds, or more than 256 MiB of system swap growth. Generation retains its
existing thermal and disk checks. Short tests have a 20-minute limit, long
tests a 60-minute limit, and conversion its existing 30-minute limit. Failed
attempts are retained. A stop is a failure of this test's resource gate, not
proof that every physical Mac with that capacity will run out of memory.

The tested residency candidate adds a 48 GiB `set_wired_limit` call, bounded
by the device's recommended working set, and retains the original 4 GiB buffer
cache. The earlier zero-cache candidate is recorded separately. Weights,
precision and model arithmetic are unchanged. MLX's
[`set_memory_limit`](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.set_memory_limit.html)
is a soft allocation guideline; it does not emulate installed RAM.
[`set_wired_limit`](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.set_wired_limit.html)
controls GPU residency. Neither function replaces the physical reservation
used by this test. The converter itself is unchanged and retains its documented
[architecture override](../../../docs/models.md#version-and-conversion-identity)
to reproduce the reference checkpoint arithmetic.

**This is not validation on a physical 64 GiB Mac, an M5 Pro, or a different
GPU configuration.** GPU resources and the operating system still identify
the actual M5 Max / 128 GiB host. Passing the lowest tested budget does not
establish the absolute minimum or guarantee arbitrary workloads.

The [machine-readable measurements](results.json) include all completed and
stopped attempts, source/model identities, input text and seeds, exact timings,
pressure and swap summaries, MP4 hashes, and hashes of retained raw evidence.
The public CLI timer includes complete AV validation. The monitor timer also
includes reservation setup/release and measurement overhead. Local paths use
roles rather than requiring a specific checkout or username.

## Reproduce a short resource test

Install the recorded version and prepare the model first. This command
deliberately reserves RAM above the requested budget, so run it alone and use
a new output directory for each attempt:

```bash
PYTHON="$PWD/.local/envs/h3/bin/python"
"$PYTHON" benchmarks/measure_resources.py \
  --budget-gib 64 --output .local/resource-check-01 --timeout 1200 -- \
  "$PYTHON" -I -m h3_apple generate \
  --prompt-file benchmarks/prompts/motion-graphics-5s.txt \
  --seed 2026 --resolution 768p --duration 5 \
  --output .local/resource-check-01/output.mp4 --timeout 1180
```

On a physical 64 GiB Mac the reservation is zero. This makes its result a
physical-machine test, which should retain its actual chip, OS and backend
identity. The script creates `result.json`, `reservation.json`, raw samples
and command logs; the CLI adds the validated MP4 and `.run.json` on success.
