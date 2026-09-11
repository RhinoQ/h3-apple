# 十条五秒提示词

保留 motion graphics、bakery 的原始短片输入，再增加八种场景。新增文本在生成前
固定为一个五秒镜头，明确主体、动作、镜头和声音，不需要参考图片或视频。
这是一组覆盖面更广的公开示例改写，不是经过 H3 成片挑选的优胜提示词。

| 新增场景 | 提示词 | 灵感来源 | 主要观察 |
| --- | --- | --- | --- |
| 老水手对白 | [sailor-dialogue](sailor-dialogue.txt) | [DeepMind：角色对白](https://deepmind.google/models/veo/prompt-guide/) | 人脸、口型、环境声 |
| 雨夜公交人像 | [night-bus](night-bus.txt) | [Google Cloud：浅景深](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) | 皮肤、反射、移动光线 |
| 糖果键盘 | [candy-keyboard](candy-keyboard.txt) | [DeepMind：视听结合](https://deepmind.google/models/veo/prompt-guide/) | 手指、小物体、拟音 |
| 峡谷升镜 | [canyon-reveal](canyon-reveal.txt) | [Google Cloud：升降镜头](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1) | 大景别、运镜、细节 |
| 玫瑰水滴 | [rose-raindrop](rose-raindrop.txt) | [Google Cloud：极近景](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) | 微距、液体、材质 |
| 黏土营地狐狸 | [clay-campfire-fox](clay-campfire-fox.txt) | [Google Cloud：营地与动画风格](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide) | 动画、双主体、音乐 |
| 林间小鼠追踪 | [field-mouse](field-mouse.txt) | [Runway：小鼠跟拍](https://help.runwayml.com/hc/en-us/articles/39789879462419-Gen-4-Video-Prompting-Guide) | 动物、毛发、跟拍 |
| 雨中撑伞 | [umbrella-opening](umbrella-opening.txt) | [MiniMax：撑伞示例](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md) | 手部、展开、雨声 |

文本为本次重新编写的五秒改写，来源、改动及哈希见 [sources.json](sources.json)。
Google Cloud 文档注明 CC BY 4.0；玫瑰与营地场景的改写保留该归属和许可说明。
其他来源提供场景灵感，未整段复制原提示词。MiniMax 指南提供声画字段与对白
标记格式，参考图片依赖已移除。来源作者未评价或背书本次结果。

[完整十条套件](../../suites/diverse-10-5s.json)可一次运行全部二十项。
本次仅补测新增八条、共十六项；原两条采用已有实测并保留批次标签。
