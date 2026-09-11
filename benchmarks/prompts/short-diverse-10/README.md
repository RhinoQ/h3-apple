# Ten five-second prompts

The suite retains the original short motion-graphics and bakery inputs and adds
eight scenes. Each new text was fixed before generation as one five-second shot,
with a subject, action, camera, and sound. No reference image or video is required.
These are broader adaptations of public examples, not prompts selected from
successful H3 outputs.

| New scene | Prompt | Inspiration | Main observations |
| --- | --- | --- | --- |
| The old sailor | [sailor-dialogue](sailor-dialogue.txt) | [DeepMind: character dialogue](https://deepmind.google/models/veo/prompt-guide/) | Face, lip synchronization, ambient sound |
| Rainy night bus | [night-bus](night-bus.txt) | [Google Cloud: shallow depth of field](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) | Skin, reflections, moving light |
| Candy keyboard | [candy-keyboard](candy-keyboard.txt) | [DeepMind: audio and video](https://deepmind.google/models/veo/prompt-guide/) | Fingers, small objects, Foley |
| Canyon reveal | [canyon-reveal](canyon-reveal.txt) | [Google Cloud: crane shot](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) | Wide scene, camera motion, detail |
| A raindrop on a rose | [rose-raindrop](rose-raindrop.txt) | [Google Cloud: extreme close-up](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) | Macro detail, liquid, materials |
| Clay campfire and fox | [clay-campfire-fox](clay-campfire-fox.txt) | [Google Cloud: campsite and animation styles](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) | Animation, two subjects, music |
| Field mouse | [field-mouse](field-mouse.txt) | [Runway: tracking a mouse](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide) | Animal motion, fur, tracking |
| Opening an umbrella | [umbrella-opening](umbrella-opening.txt) | [MiniMax: umbrella example](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md) | Hands, unfolding, rain sound |

These five-second adaptations were rewritten for this comparison.
[sources.json](sources.json) records sources, changes, and hashes. Google Cloud
documentation is marked CC BY 4.0; the rose and campsite adaptations retain
that attribution and license notice. Other sources provided scene inspiration
without copying complete prompts. The MiniMax guide supplied audiovisual fields
and dialogue tags; reference-image dependencies were removed. Source authors
have not reviewed or endorsed these results.

The [complete suite](../../suites/diverse-10-5s.json) runs all twenty generations.
This extension ran only the sixteen new entries, retaining the two original
pairs with explicit round labels. Display titles in `sources.json` were translated
for the [English edition](../../../docs/evidence/english-edition.json); prompt
bytes and pre-generation hashes are unchanged.
