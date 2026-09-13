# H3 Apple video studies

An independently authored GitHub Pages gallery of local MiniMax H3 generations.
The case index comes from [fal's H3 guide](https://fal.ai/learn/devs/minimax-h3-prompting-guide).
The gallery publishes original local outputs and generation metadata, with clear
status for every case. It does not imply that every listed case has been generated.

Open `index.html` through a static HTTP server. No JavaScript framework, remote
font, analytics, API key, or cloud generation service is required. The small
`reproduction.js` helper copies commands. The page has no file chooser or upload.

`build.py` consumes the private source inventory and local run status using the
H3 Apple Conda environment. It exports an explicit allowlist of metadata and
copies only completed H3 Apple output files. The private inventory and source
media stay outside this repository. `layout.html` and `styles.css` are the page
sources; `index.html`, `collection.json`, and `records/` are generated exports.

Each case displays its exact prompt with a copy button and source attribution,
ordered reference previews, an input-fetching command, and the Python API call.
Follow [REPRODUCE.md](REPRODUCE.md) for pinned
runtime installation and model preparation. `reproduce.py` reads the prompt
from the published case record, downloads reference media from the source,
and checks the runtime and model manifest before running.

GitHub Pages can serve this repository directly from the root of its publishing
branch. The `.nojekyll` file preserves the authored static files.

## Reproduction limits

- Published prompts are excerpts; the full original requests and seeds are unknown.
- The first batch uses H3 Apple `0.1.0.dev2`, four steps, seed 42, and 576p output.
- Mixed video/audio, portrait and first/last-frame cases use the isolated
  `0.1.0.dev3+guide2` development build. Each record includes the actual runtime
  source hash, model identity and attention mode. These input extensions are
  experimental. Their pinned source is public on `codex/guide-inputs`; they
  are not included in the latest tagged runtime release.
- First/last-frame cases use native FL2VA with LightX2V FL four-step v0.1 and
  dense attention. T2VA and Ref2VA retain their established four-step weights.
- The source videos are 720p. A source clip of 15.083 seconds is delivered as
  15 seconds by the current product API. Every record retains both geometries.
- The first verified binocular study is reused, with its original measurement.
- Case 15 uses its three published images; the reference video mentioned in its
  source prompt is not published. The case explicitly discloses this difference.
- Case 27 is delivered as five seconds because its source output is below the
  runtime's five-second minimum.
- Missing video, audio, frame-conditioning, or aspect-ratio support is explicit.
- Technical completion and creative quality are separate. The collection does
  not assign a quality pass merely because an output validates.

## Attribution and content

The implementation, writing, and visual identity of this page were authored
independently. Prompts are reproduced from the linked guide as the recorded model
inputs; this repository's code license does not relicense third-party prompts or
reference media. The page does not include fal's site code, logo, surrounding article, or
hosted output videos. Reference previews are served from the source URLs;
the input assets themselves remain outside this repository.

Generated studies may contain names or visual subject matter from their source
inputs. They are presented as technical reproductions, not endorsements or
claims of ownership of third-party brands or underlying reference material.
No blanket rights or licenses to third-party subject matter are granted.

H3 Apple is not affiliated with fal, MiniMax, or Apple. See the
[runtime repository](https://github.com/RhinoQ/h3-apple) for model and dependency
licenses.
