# Two additional fifteen-second prompts

These scenes extend motion graphics and bakery with a character-and-prop
narrative and continuous motion in a wide landscape. Both use one shot, full
audio, and no reference image. Texts and seeds were fixed before generation,
without selecting or rewriting them based on outputs.

| Scene | Prompt | Inspiration | Main observations |
| --- | --- | --- | --- |
| The hidden key | [archive-discovery](archive-discovery.txt) | [Google Cloud: an object hidden in an old book and reaction to a noise](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide#action) | Hands, persistent key, discovery → noise → reaction, dialogue synchronization |
| Crystal flowers | [lunar-flower-walk](lunar-flower-walk.txt) | [DeepMind: lunar crystal flowers in “Build a world”](https://deepmind.google/models/veo/prompt-guide/) | Walking and footprints, subject continuity, blooming, tracking, light, sound |

The English prompts were adapted for fifteen seconds. [sources.json](sources.json)
records the specific changes and sources. The first adaptation retains the
Google Cloud documentation's [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
attribution. The second uses the public setting as inspiration for new action,
camera, and sound direction. Audiovisual fields, the single-shot format, and
dialogue tags follow the [MiniMax H3 writing guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md).
These references do not imply that their authors or platforms validated the
quality of these H3 outputs.

The [two-prompt suite](../../suites/cinematic-two-15s.json) uses the existing
Ours/vpipe VDN recipes for four generations. Human acceptance requires viewing
the complete fifteen-second audiovisual outputs; acceptance of earlier videos
does not extend to these. Display-title translation is documented in the
[English edition](../../../docs/evidence/english-edition.json), with prompt bytes unchanged.
