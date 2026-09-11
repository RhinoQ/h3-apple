# 原生三方比较：native-three-02

六次独立尝试已经结束，四条完整声画交付通过，两个官方 FastVideo 调用拒绝指定规格。
本轮于 2026-09-10 UTC 运行，机器为 **Apple M5 Max / 128 GiB / macOS 26.6.1**。
每项只运行一次，是固定公开输入上的系统观察。四条成功视频随后均获
[用户人工声画接受](../../reviews/existing-eight-20260911.json)；原始 JSON 中的
`pending` 保留为运行结束时快照，不改写历史测量。

| 入口 | motion graphics | bakery |
| --- | ---: | ---: |
| FastH3 / Ours | 36 分 47 秒 | 33 分 18 秒 |
| 官方 FastH3 / VSA | 入口拒绝规格 | 入口拒绝规格 |
| vpipe / VDN | 41 分 15 秒 | 39 分 30 秒 |

耗时从新进程启动前到完整最终声画校验通过，含加载、编译、生成、封装和外部入口的
交付转换；准备与等待散热不在该数值中。普通系统与 Metal cache 保留，每个提示词
均用新的进程/空提示词缓存。顺序固定为 motion graphics 后 bakery，每个输入内
依次 Ours、官方 FastH3、vpipe。全部完成项没有 swap 增长或触发资源保护。

权威导出为 [results.json](results.json)，表和 [CSV](results.csv) 从它生成。它包含
源码、实际环境文件和模型凭据身份、完整媒体检查、精确秒数及原始本地结果/配置/日志
哈希。`$PRODUCT`、`$MODELS` 代表本机路径角色，不是可直接执行的命令。
原始不可覆盖记录位于本机 `.local/comparisons/native-three-02/`。

## 输入与实际配置

交付 **1366×768、360 帧、15.000 秒、24fps、32 kHz 立体声**；实际模型生成
1376×768 / 362 帧，只居中裁切和截尾，无放大或插帧。完整文本与种子由
[公共 suite](../../suites/motion-bakery.json) 固定：motion graphics / 2026、bakery / 87001。
两条均是已见输入，相同 seed 不代表跨引擎相同噪声。

| 入口 | 实际源码与配方 |
| --- | --- |
| Ours | `cc15b89156fbebf96be46d2573ab955972017ad0`，`ours-v1`；固定 native FL2VA + 官方 VSA adapter 的 INT8/group64 转换，完整 VAE；两次均实际 4 NFE、200 次直接稀疏调用、零 fallback |
| 官方 FastVideo | `a943220c115228ade5d57b3bab9a6a87fd600a10`，未经修改的 MLX CLI，VSA auto/reference、四步、完整 FP32 VAE，关闭 fast/fast-spatial；本机转换资产的 base/adapter 在 JSON 中明确，并非完整 student snapshot 等价声明 |
| 官方 vpipe | `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`，未经修改的官方 VDN 模板；FL2VA Q8、VDN stage-dmd、Turbo v4 adapter，配置六步、shift 12/3、i8_gemm；入口未直接报告真实 NFE，保留未知 |

Ours 普通安装包运行源码 SHA256 为
`b4e92640c42c85e04628308ff7929647f47866f58f3dd029d321eaf125027dab`，
新准备的模型 bundle 身份为
`6b2716e05fd19c8d554a609bc97e46ef29c504e81f1798b02008ea003670b942`。
后续文档、示例和分发提交不改写本轮测量版本；运行文件相同的分发包另附身份核对。

Ours 去噪阶段记录的 MLX peak memory 分别为 **54.08 / 53.66 GiB**；这不是进程或
整机统一内存峰值。vpipe 没有相同口径的内部数据，不填推测值。

## 官方入口限制与结论边界

两次未经修改的官方 FastVideo 调用都在模型加载前返回：

```text
ValueError: H3 generates 5-15 s at 24 fps; 362 frames is 15.08 s.
```

该状态只说明这个固定版本入口拒绝所需对齐形状；不代表其他版本、时长或 FastH3
模型均不能使用。不以失败退出耗时参与排序，不给官方代码加入 Ours 修复后继续
称为未经修改的对照。更短规格可以另立新比较，本轮不偷换工作量。

四条成功视频通过了完整声画解码与严格最终规格检查，但这不能替代人工质量接受。
缩略图和 [两条 Ours 可播放预览](../../../examples/README.md) 只帮助查看；原生视频
文件名和 SHA 在 JSON 中，四条完整视频另备分发附件。当前没有已发布下载地址。

这些系统使用不同权重/adapter/精度/配方，且没有重复样本或独立留出数据。
此表不证明某个算子的增量贡献、稳定速度优势、新算法提速或总体质量胜出。
下一次提速 Proposal 应匹配比较 Ours 稳定版与候选，依其事前速度和质量门判断。
