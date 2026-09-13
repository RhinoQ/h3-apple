# Ref2VA and terminal-progress integration

The public CLI reproduced all three recorded baseline MP4 files byte for byte.
Both Ref2VA cases also reproduced every baseline diagnostic array: reference
conditioning, initial noise, all four steps, final latents, video before encoding
and raw audio. The text case checked the complete MP4, without diagnostic export.

| Regression | Delivered video | Observed CLI time | MP4 match | Diagnostic arrays matched |
| --- | --- | ---: | --- | ---: |
| One reference image | 576p, 5 seconds | 322.457 s | Exact | 28 |
| Four ordered references | 576p, 15 seconds | 1328.640 s | Exact | 32 |
| Text: amber marble | 576p, 5 seconds | 275.271 s | Exact | Not exported |

Each run completed four denoising steps, 200 direct NAX sparse calls and zero
fallbacks, with no swap growth. Progress increased from 5% to 100% for denoising,
then reported decoding and validation; `Complete` followed validated publication.
Stdout remained valid result JSON. The independent installed package passed
183 tests, including terminal/redirection behavior, cancellation, ordered image
inputs, optional-dependency errors and self-contained model bundles.

[results.json](results.json) is the authoritative record of full prompts,
ordered reference URLs and hashes, model payload hashes, baseline and candidate
source identities, backend, phase times, array checks and raw-file hashes.
The four images follow webpage order: building, person, flag, glasses close-up.
The original displayed prompt was retained, including its person/flag numbering
mismatch. No parameter or input was selected using this regression.

These are single observed regression times on M5 Max / 128 GiB / macOS 26.6.1.
The host reported fair thermal state during part or all of these runs. The
reference runs include diagnostic export. These timings do not establish a
new speed improvement or repeatable speed guarantee. Models were reused from
local files; no new model conversion or full download was tested here.

The reference outputs retain the earlier user acceptance of these two cases.
There was no new blind or human review. Other image counts, 768p Ref2VA,
smaller-memory machines and video/audio references remain outside this result.
See [Ref2VA setup](../../../docs/ref2va.md) and the
[public API](../../../docs/api.md) to reproduce the recorded requests.

Raw outputs, logs and arrays are retained under
`.local/integration/ref2va-progress-01/`; installed-wheel tests are under
`.local/distributions/ref2va-progress-final/`. These are local evidence paths,
not public download links. This integration does not publish a new tag or release.
