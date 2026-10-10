---
name: h3-apple-ref2va-prompting
description: Generate and review reference-image videos with h3-apple on Mac, including environment setup, Ref2VA prompts, shot planning and audiovisual continuity.
---

# H3 Apple Ref2VA

This local skill supplements MiniMax's official prompting guide. Preserve the
brief's subjects, reference roles, motion, timing and audio. Consult project
records for budgets, preferences and prior work; those are project context,
not universal prompt rules.

## Deliver the requested work

- **Generate a video:** use the public h3-apple CLI/API through setup, rendering,
  review and delivery. Read [local generation](references/local-generation.md).
  Reuse working installations; install missing components within authorization.
  A prompt or readiness check is not a finished video.
- **Write a prompt or plan:** deliver the text without installing or running models.
- **Review a video:** inspect the existing output; generation setup is unnecessary.

Honor explicit versions and delivery settings. Large downloads and publication
require their own authorization. Do not expand the task into engine changes.

## Prepare inputs

Inspect relevant references. Read [input scope](references/input-scope.md) when
selecting assets or mapping subjects to shots. Preserve requested subjects;
do not remove them to avoid model failures. Assign incidental characters in a
style image to its intended role, not automatically to the cast. Crop or edit
references only within the user's scope.

For sequences and review, read [continuity](references/story-continuity.md).
Derive criteria from the brief and creative form. Judge the output, not the
plausibility of its prompt.

## Write a Ref2VA prompt

For a new complete prompt, use these fields in order:

`subject_definitions`, `summary`, `retention_analysis`,
`detailed_description`, `overall_soundscape`, `non_diegetic_music`.

Explain in the user's language; write prompt sections in English. Preserve
requested dialogue, lyrics and visible text in their original language.
Explicit user instructions override this default.

Define reusable identity/style as `<Subject N>`, citing `<Picture N>`.
Use standalone picture definitions for frame/storyboard anchors.
Keep labels consistent. In `retention_analysis`, map subjects to shots and use
the official retention markers for each role.

Begin with `[Shot 1]`; later cuts use `[Shot N] At MM:SS.mmm, ...`.
Describe visible actions, framing and sound. Fit timing to the requested duration.
Prefer concrete descriptions over accumulated prohibitions; consult the pinned
guide for exact syntax.

h3-apple accepts image references and generates audio. Do not invent video/audio
inputs or `<Audio N>` assets for background music. Keep voices, effects and score
consistent across visual and audio fields.

Treat speech and visible text separately. Dialogue language does not imply
subtitles. For caption-free delivery, specify spoken dialogue without overlays
while preserving requested signs or other scene text. Verify the actual result.

## Review and revise

For input audits, show the reference selection/renumbering and exact text edits.
Preserve requested beats; avoid unrelated style or framing changes.
Keep frozen experiments immutable and register prompt changes before generation.

Read [output comparison](references/output-comparison.md) when comparing renders
or diagnosing quality. Separate prompt, runtime and postprocessing changes when
attributing results. Report inspected evidence and uncertainty; a proposed
correction is not a tested fix.
