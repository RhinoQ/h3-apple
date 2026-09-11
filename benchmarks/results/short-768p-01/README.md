# 768p / 5 秒比较

**准备中，尚无本轮成片结果。** 用户决定五秒比较 Ours、官方 FastH3 和 vpipe，
十五秒继续只比较 Ours、vpipe。两个场景及种子由
[短片套件](../../suites/motion-bakery-5s.json)固定，提示词在生成前缩写为五秒动作。

共同交付为 1366×768、120 帧、24fps、5.000 秒、32 kHz 立体声。
各路线原生生成 1376×768 / 124 帧，再按同一规则裁切、截尾，使用完整 H3 VAE。
每个场景每条路线一次观察，记录进程启动至完整声画验收的耗时和失败。
本轮不预设赢家；人工画质和音频接受与机器媒体通过分开记录。

官方路线固定为未修改 FastVideo `a943220c115228ade5d57b3bab9a6a87fd600a10`，
Preview v1 Dense DataFree、四步、INT6 / group64、BF16 激活、完整 FP32 VAE，
不开 VSA、插帧或降分辨率。官方公开验证是 832×480 / 124 帧；本轮 768p 需要重新
验收。先运行独立的官方 presenter 短片，完成后才把官方纳入两个场景。
Ours、vpipe 保留各自稳定配方；三路权重与算法不同，属于完整系统比较。

准备阶段的 44 项相关回归通过，覆盖套件路线选择、原片 AAC 正负尾部舍入、交付
音频覆盖、严格最终验收和进程边界。已安装新的普通 Ours wheel，并恢复官方未修改
FastVideo 安装。短片最大 packed 行数 38,752，SwiGLU 中间张量有 1,111,097,344 个
元素；在官方 MLX 0.32.2 下，精确值算子检查全部正确。它只是运行前检查，不是成片。

## 权重准备

2026-09-10 核对发现，[官方 INT6 模型卡](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-Dense-DataFree-MLX-INT6)
虽然记录了成功成片、导出大小和 SHA256，当前 `81ee7a77` 仓库只包含说明和元数据，
实际 `mlx_h3_dit.safetensors` 地址返回 404；没有找到其他公开分支或 tag。
机器可复核记录见 [preparation.json](preparation.json)。

可按官方转换流程，从 Dense DataFree 固定版本 `f624f08c` 准备 INT6。
现有文本编码器的 14 个分片 SHA256 与官方一致，可复用约 66.7 GB；原始 DiT、
官方 VAE 等尚需下载约 77.3 GB。依照研究项目的下载约定，已请求本次最多 80 GB
下载授权，收到授权前不开始模型下载。现有 VSA 权重不冒充这份官方 Dense 模型。

完整准备证据、事前方案和后续执行记录在产品仓库的
`.local/validation/official-short-768p-01/`。已有十五秒失败、历史 P084 结果保持原样。
