# Reference roles and shot scope

Distinguish an asset, the subjects it depicts and its intended role. A reference
may supply identity, appearance, style, composition or a frame anchor. Its
incidental contents do not automatically become requested cast or staging.
Clarify an ambiguous role when it materially affects the result.

Several images or views can describe one subject; one image can contain several
subjects. Map `<Picture N>` to the actual input order and use stable
`<Subject N>` labels for reusable identities or content. When selecting or
reordering assets, update their citations consistently. Preserve distinct
roles even when their appearances match.

Specify subject membership and retained attributes for the relevant shots in
`retention_analysis`. Describe visible subjects, relationships and actions in
each shot. Scope composition requirements to the shots where they apply rather
than attaching a stock framing paragraph to an entire production. Retain
references needed across different shots, even when their subjects never share
the frame. Do not remove a requested subject as a shortcut to reliability.

A reference selected for identity need not dictate the starting composition.
Use standalone picture definitions for intended frame or storyboard anchors.
Select sufficient relevant context without importing an unrelated asset
library. Input scoping can expose contradictions; it does not guarantee subject
count, identity preservation, motion or timing in the generated result.

## Pinned upstream guidance

The official source snapshot is MiniMax-H3 commit
`d21241f0a4b3acbb34c97dae47fa417b7065e438`; file hashes and the original check
date are in [sources.json](sources.json). These links define prompting syntax,
not demonstrated quality or performance for a particular local runtime.

- [Official prompting skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/SKILL.md)
- [Ref2VA guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/references/ref-en.txt)
- [Audio and visual syntax](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/skills/h3-prompt-writing/references/base-en.txt)
- [Upstream installation and workflow context](https://github.com/MiniMax-AI/MiniMax-H3/blob/d21241f0a4b3acbb34c97dae47fa417b7065e438/README.md)

Consult the pinned guide when exact syntax matters. Keep local experiment
protocols, examples, outcomes and adoption decisions in their project records;
do not present them as universal properties of the prompt format.
