# 两条新增十五秒提示词

在既有 motion graphics / bakery 之外增加两种场景，分别观察人物道具叙事与大景别连续运动。
两条均为单镜头、完整声画、无需参考图；文本和种子在生成前固定，不按生成结果挑选或改写。

| 场景 | 提示词 | 场景来源 | 主要观察 |
| --- | --- | --- | --- |
| 古书密钥 | [archive-discovery](archive-discovery.txt) | [Google Cloud：Action 中旧书藏物与异响反应示例](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/video-gen-prompt-guide#action) | 手部、钥匙持续存在、发现→异响→反应的顺序、对白口型 |
| 月地晶花 | [lunar-flower-walk](lunar-flower-walk.txt) | [DeepMind：Build a world 中月地晶体花示例](https://deepmind.google/models/veo/prompt-guide/) | 行走与脚印、主体一致性、开花过程、跟拍与光影、音效 |

英文文本是本次面向十五秒的改写，具体改变和来源见 [sources.json](sources.json)。
第一条改写遵循 Google Cloud 文档的 CC BY 4.0 归属要求。
第二条以公开场景为灵感重新编排动作、镜头和声音。
声画字段、单镜头和对白标记遵循
[MiniMax H3 官方写作指南](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/42ed227ee7df40d41602854ae760620d6eb651fe/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)。
这些来源提供写作依据，不代表作者或原平台已验证本次 H3 输出质量。

[新增两条套件](../../suites/cinematic-two-15s.json)使用既有 Ours / vpipe VDN 配方，共四次生成。
评价完整十五秒声画后再记录人工接受；先前视频的接受不延伸到新视频。
