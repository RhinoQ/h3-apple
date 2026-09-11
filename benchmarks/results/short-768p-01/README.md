# 768p / 5 秒比较

**Ours / vpipe 四条成片已完成；用户随后取消官方对照，本轮按两路比较结束。** 本轮于
2026-09-11 UTC 在 Apple M5 Max / 128 GiB / macOS 26.6.1 上执行；十五秒只保留
Ours / vpipe 比较。提示词在生成前缩写为五秒动作。原始 JSON 保留当时的三路计划
和实际四项顺序；当前[短片套件](../../suites/motion-bakery-5s.json)按用户决定只选择
Ours / vpipe，输入与种子不变。[范围决定](decision.json)记录取消，未重写测量数据。

| 入口 | motion graphics | bakery |
| --- | ---: | ---: |
| FastH3 / Ours | 5 分 54 秒 | 5 分 55 秒 |
| vpipe / VDN | 8 分 49 秒 | 9 分 01 秒 |

本次 Ours 的等待时间分别减少 **32.96% / 34.33%**，vpipe 耗时分别为 Ours 的
1.492 / 1.523 倍。每项只有一次观察，不是重复测量得到的稳定倍率，也不代表画质胜出。
精确秒数、配方、运行时文件身份、原始记录哈希和媒体检查由
[results.json](results.json)维护，[CSV](results.csv)为同源导出。

共同交付为 1366×768、120 帧、24fps、5.000 秒、32 kHz 立体声。
各路线原生生成 1376×768 / 124 帧，再按同一规则裁切、截尾，使用完整 H3 VAE。
计时从新进程启动前到完整声画解码与规格校验通过，包含模型加载、编译、生成、
封装和交付裁切。普通系统与 Metal cache 保留，每次使用空提示词缓存；准备和等待
散热不计入。实际顺序为 motion graphics / Ours、vpipe，然后 bakery / Ours、vpipe。
先完成这四项、另行补测官方是生成前声明的安排，未按结果挑选或重跑。

四条均通过严格交付检查，无 swap 增长，始终接电，温度仅为 nominal / fair。
每条抽查覆盖首尾的 12 帧，没有看到明显后段损坏：
[motion graphics / Ours](diagnostics/motion-graphics-ours.jpg)、
[motion graphics / vpipe](diagnostics/motion-graphics-vpipe.jpg)、
[bakery / Ours](diagnostics/bakery-ours.jpg)、[bakery / vpipe](diagnostics/bakery-vpipe.jpg)。
这是具名缩略图检查，未替代完整动作与音频评价；人工声画接受全部为 `pending`。

## 实际配方与边界

Ours 固定产品 `1e7890a41a7c2039b46fbdfcc04dbb28a09b0010`、普通 wheel、`ours-v1`；
native FL2VA + 官方 VSA adapter 的 INT8/group64 转换和既有加速 VAE 未改变。
两次均实际 4 NFE、200 次稀疏调用、零 fallback；去噪 MLX peak 为 33.12 / 33.11 GiB。
这不是整机内存峰值。

vpipe 固定未修改上游 `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` 的 VDN 模板，
FL2VA Q8、VDN stage-dmd、Turbo v4 adapter、shift 12/3、i8_gemm。
配置六步，但本轮原生日志实际显示五步 schedule、250 个去噪 block；结构化真实 NFE
与同口径内部峰值未报告，保留未知。不同引擎的相同 seed 不代表相同噪声。

各系统权重、精度、步数和算法不同，本次耗时差不能全部归因于某项优化。
没有留出数据或重复样本，不推出总体质量、稳定提速或官方路线的快慢。
原始不可覆盖证据位于 `.local/comparisons/short-768p-01/`，导出中的 `$PRODUCT`、
`$MODELS` 是本机路径角色。上一轮十五秒数据及失败现场保持原样。

## 已取消的官方准备（历史）

原计划官方路线固定为未修改 FastVideo `a943220c115228ade5d57b3bab9a6a87fd600a10`，
Preview v1 Dense DataFree、四步、INT6 / group64、BF16 激活、完整 FP32 VAE，
不开 VSA、插帧或降分辨率。官方公开验证是 832×480 / 124 帧；本轮 768p 需要重新
验收。计划先运行独立的官方 presenter 短片，再纳入两个场景；取消前均未执行，
没有官方成功耗时。

准备阶段的 44 项相关回归通过，覆盖套件路线选择、原片 AAC 正负尾部舍入、交付
音频覆盖、严格最终验收和进程边界。已安装新的普通 Ours wheel，并恢复官方未修改
FastVideo 安装。短片最大 packed 行数 38,752，SwiGLU 中间张量有 1,111,097,344 个
元素；在官方 MLX 0.32.2 下，精确值算子检查全部正确。它只是运行前检查，不是成片。

### 权重核对记录

2026-09-10 核对发现，[官方 INT6 模型卡](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-Dense-DataFree-MLX-INT6)
虽然记录了成功成片、导出大小和 SHA256，当前 `81ee7a77` 仓库只包含说明和元数据，
实际 `mlx_h3_dit.safetensors` 地址返回 404；没有找到其他公开分支或 tag。
机器可复核记录见 [preparation.json](preparation.json)。

可按官方转换流程，从 Dense DataFree 固定版本 `f624f08c` 准备 INT6。
现有文本编码器的 14 个分片 SHA256 与官方一致，可复用约 66.7 GB；原始 DiT、
官方 VAE 等原预计仍需下载约 77.3 GB。此前请求的最多 80 GB 下载随官方对照取消，
没有启动模型下载。[preparation.json](preparation.json)保留取消前的核对状态。

完整准备证据和事前方案在 `.local/validation/official-short-768p-01/`；四条成片的
完成后核验与导出脚本在 `.local/validation/short-768p-results-01/`。
