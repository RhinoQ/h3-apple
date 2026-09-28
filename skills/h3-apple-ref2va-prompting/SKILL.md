---
name: h3-apple-ref2va-prompting
description: Generate and review reference-image videos with h3-apple on Mac, including environment setup, Ref2VA prompts, shot planning and audiovisual continuity.
---

# H3 Apple Ref2VA

This locally authored skill supplements MiniMax's official `h3-prompt-writing`
guide. Preserve the requested creative intent, subjects, motion, timing, audio
and reference roles. Keep project preferences, production budgets and experiment
history in the project's records; consult them when continuing existing work.
They are context for that production, not universal requirements of this skill.

## Follow the requested deliverable

When the user asks to make or render a video, use the installed **h3-apple** CLI
or Python API and carry the task through setup, generation and delivery. Read
[local-generation.md](references/local-generation.md) to find or install a
compatible Conda environment, check readiness and download requirements, run the
generation and locate the finished MP4. Reuse a working installation; install
missing components within the authorized task instead of handing the user
installation commands. Do not stop after writing a prompt when a video was
requested.

For prompt writing, story ideas or shot plans alone, deliver that artifact without
installing h3-apple or running models. Reviewing an existing video also does not
require generation setup. Preserve an explicitly requested product version and
delivery settings. A generation request authorizes the necessary local workflow;
large-download consent and publication remain separate boundaries.

## Prepare the actual input

Inspect supplied references when their role or contents matter. Read
[input-scope.md](references/input-scope.md) when selecting assets or mapping
references and subjects to shots; it also links the pinned official syntax.
Use only the reference roles and composition constraints relevant to each shot,
without dropping requested content to avoid a generation failure. Prefer a
concrete account of what is visible and happening over accumulating prohibitions.

Style references with incidental characters should be assigned the intended
style role; they do not automatically define additional cast. Do not crop or
edit a supplied reference unless that is within the user's requested work.

For sequence planning or delivery review, read
[story-continuity.md](references/story-continuity.md). Derive continuity and
performance criteria from the brief and creative form. Judge the actual output;
a plausible prompt or successful technical check does not establish that the
output fulfills the brief.

## Official Ref2VA output

For a new complete prompt, use these fields in order:
`subject_definitions`, `summary`, `retention_analysis`, `detailed_description`,
`overall_soundscape`, `non_diegetic_music`. Explain to the user in their language;
write the prompt sections in English while preserving requested dialogue,
lyrics and visible text in their original language. Explicit user instructions
take precedence over this default.

Define reusable identity/style content as `<Subject N>` and cite its source
`<Picture N>`. A standalone picture definition is for a frame or storyboard
anchor. Reuse each label consistently. Use `retention_analysis` to map each
subject to its shots and state what is retained; use the official retention
markers according to the declared role. Start with `[Shot 1]`; later cuts use
`[Shot N] At MM:SS.mmm, ...`. Write concrete visible actions, framing and sound
in each shot, not just a list of references. Timing must fit the requested
duration. Consult the pinned official guide for detailed syntax and examples.

h3-apple's current task is image-reference generation with generated audio.
Do not invent video/audio reference inputs or `<Audio N>` assets from requests
for background music. Keep voices, sound effects and score consistent across
the shot descriptions and the two audio fields.

Treat spoken content and visible text as separate requirements. A requested
dialogue language does not imply subtitles. Specify captions, overlays and
in-scene writing according to the brief. When caption-free delivery is requested,
state that dialogue is spoken without overlaid subtitles; preserve any requested
signs or other scene text. Verify these requirements in the resulting output.

## Keep evidence and changes separate

For an input audit, show the actual reference selection/renumbering and the precise
text edits. Preserve requested beats; avoid opportunistic style or framing
rewrites. If comparing a frozen experiment, keep it immutable and register any
new prompt/schema change as a separate intervention before generation.

When comparing renders or diagnosing a quality change, read
[output-comparison.md](references/output-comparison.md). Separate prompt changes
from generation settings, editing and postprocessing when attributing a result.
A proposed correction is not a tested fix; report what was actually inspected
and what remains uncertain. Do not expand a prompt-only or review request into
generation, or a generation request into publication or engine changes.
