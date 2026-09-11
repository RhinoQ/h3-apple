# 真实生成示例

以下来自 [native-three-02 正式运行](../benchmarks/results/native-three-02/README.md)，
使用完整公共提示词，原始生成与交付均为 768p、15 秒、24fps、立体声。
仓库内的 MP4 是 **640×360 的小型重编码预览**，保留完整 15 秒声画；
它们的分辨率不用于衡量原生成画质或生成耗时。对应原生文件 SHA 和预览 SHA 见
[manifest](previews/manifest.json)。原生声画已获
[用户接受](../benchmarks/reviews/existing-eight-20260911.json)。

## Motion graphics / seed 2026

[播放完整 15 秒的小预览](previews/motion-graphics-ours.mp4) ·
[完整提示词](../benchmarks/prompts/motion-graphics.txt)

[![Motion graphics 固定间隔缩略图](previews/motion-graphics-ours.jpg)](previews/motion-graphics-ours.mp4)

## Bakery / seed 87001

[播放完整 15 秒的小预览](previews/bakery-ours.mp4) ·
[完整提示词](../benchmarks/prompts/bakery.txt)

[![Bakery 固定间隔缩略图](previews/bakery-ours.jpg)](previews/bakery-ours.mp4)

## 原生视频与复现

四条原生 MP4（Ours 与 vpipe 各两条）已准备为独立分发附件，未上传公开地址。
文件身份、完整秒数和模型/环境信息见结果 JSON；原始实验文件继续保留。
三秒固定间隔的缩略图未经人工挑帧；vpipe 的缩略图为
[motion graphics](previews/motion-graphics-vpipe.jpg) 与 [bakery](previews/bakery-vpipe.jpg)。

从产品仓库使用准备好的 Ours 环境：

```bash
"$PWD/.local/envs/h3/bin/python" -m h3_apple generate --prompt-file benchmarks/prompts/motion-graphics.txt --seed 2026 --output motion-graphics.mp4
"$PWD/.local/envs/h3/bin/python" -m h3_apple generate --prompt-file benchmarks/prompts/bakery.txt --seed 87001 --output bakery.mp4
```

提示词原文保持不变。当前接口是文字到声画视频，没有传入参考图，也不保证按提示词
逐镜头精确执行或文字始终准确。自由提示词的 Python 调用见 [generate.py](generate.py)。
