# 768p / 5 秒：十提示词对比

**新增 16 次全部成功交付，合并原两组后共 10 个提示词、20 条视频。十组中 Ours 等待时间均更短。**
新增八组平均少等待 35.1%；全部十组平均少等待 34.8%。这是固定配方的系统耗时观察，新增视频的人工质量评价仍待完成。
原两组沿用 [short-768p-01](../short-768p-01/README.md) 的精确输入、视频和原始耗时，没有计作本轮新生成。
本轮在 2026-09-11 UTC、Apple M5 Max / 128 GiB / macOS 26.6.1 上完成，批次墙钟约 2 小时 19 分钟，未重跑或选片。

[提示词与原始来源](../../prompts/short-diverse-10/README.md) · [生成前固定的方案](plan.json) · [完整机器结果](results.json) · [新增 16 项 CSV](results.csv)

## 等待时间

表中为每个输入各一次完整交付，格式为分:秒，四舍五入到秒。精确值及聚合公式输入以 `results.json` 为准。

| 场景 | 批次 | Ours | vpipe / VDN | Ours 等待减少 |
| --- | --- | ---: | ---: | ---: |
| Motion graphics | 既有 | 5:54 | 8:49 | 33.0% |
| Bakery | 既有 | 5:55 | 9:01 | 34.3% |
| 水手对白 | 新增 | 5:56 | 8:57 | 33.8% |
| 雨夜公交 | 新增 | 6:02 | 9:08 | 33.9% |
| 糖果键盘 | 新增 | 5:41 | 9:11 | 38.1% |
| 峡谷升镜 | 新增 | 6:06 | 9:10 | 33.4% |
| 玫瑰水滴 | 新增 | 6:06 | 9:13 | 33.8% |
| 黏土营地狐狸 | 新增 | 5:49 | 9:10 | 36.6% |
| 小鼠跟拍 | 新增 | 6:07 | 9:12 | 33.6% |
| 雨中撑伞 | 新增 | 5:47 | 9:14 | 37.4% |

| 覆盖 | Ours 平均 / 中位数 | vpipe 平均 / 中位数 | 总等待减少 | vpipe/Ours 总耗时比 |
| --- | ---: | ---: | ---: | ---: |
| 新增 8 组 | 5:57 / 5:59 | 9:09 / 9:10 | 35.1% | 1.540 |
| 全部 10 组（含既有 2 组） | 5:56 / 5:55 | 9:07 / 9:10 | 34.8% | 1.534 |

全部十组累计等待为 Ours 59:24、vpipe 91:05，相差 31:42。此处累计的是各项交付计时，不含批次间散热等待。
减少比例为 `1 − sum(Ours)/sum(vpipe)`；每对倍率另存于结果文件。不同提示词不是同一输入的重复试验，不据此给出重复测量置信区间或稳定倍率。

## 成片与质量

新增 16 条均通过最终媒体完整解码、尺寸、时长、帧数、帧率、声道和采样率检查；视频 SHA256 与每条原始记录全部一致。
新增八个 Ours 均实际执行 4 NFE、200 次直接稀疏调用、零 fallback。每条抽查包含首尾在内的 12 帧，未看到明显后段坏图。
这是具名缩略图检查，未试听音频，不能替代完整动态声画评价。已看到的提示词遵循问题保留如下：

- **Ours / 黏土营地狐狸**：提示词描述一名露营者与一只狐狸，抽帧显示两人、两狐。多主体问题需计入质量判断。
- **vpipe / 小鼠跟拍**：末尾目标是圆卵状物体，在缩略图中不能清楚辨认为提示词要求的蘑菇。
- 两方糖果键盘的键帽字符均不规则；精确按键次数、撑伞手部与机构、对白及音画同步，需要观看完整视频。

上述视频没有删去、重跑或替换，也没有因画面问题移除其成功交付耗时。速度表不宣称总体质量胜出。
此前八条视频的[用户验收](../../reviews/existing-eight-20260911.json)只绑定旧视频哈希，其中四条是本表复用的短片；新增十六条的人工声画接受均为 `pending`。

| 新增场景 | Ours 抽帧 | vpipe 抽帧 |
| --- | --- | --- |
| 水手对白 | [查看](diagnostics/sailor-dialogue-ours.jpg) | [查看](diagnostics/sailor-dialogue-vpipe.jpg) |
| 雨夜公交 | [查看](diagnostics/night-bus-ours.jpg) | [查看](diagnostics/night-bus-vpipe.jpg) |
| 糖果键盘 | [查看](diagnostics/candy-keyboard-ours.jpg) | [查看](diagnostics/candy-keyboard-vpipe.jpg) |
| 峡谷升镜 | [查看](diagnostics/canyon-reveal-ours.jpg) | [查看](diagnostics/canyon-reveal-vpipe.jpg) |
| 玫瑰水滴 | [查看](diagnostics/rose-raindrop-ours.jpg) | [查看](diagnostics/rose-raindrop-vpipe.jpg) |
| 黏土营地狐狸 | [查看](diagnostics/clay-campfire-fox-ours.jpg) | [查看](diagnostics/clay-campfire-fox-vpipe.jpg) |
| 小鼠跟拍 | [查看](diagnostics/field-mouse-ours.jpg) | [查看](diagnostics/field-mouse-vpipe.jpg) |
| 雨中撑伞 | [查看](diagnostics/umbrella-opening-ours.jpg) | [查看](diagnostics/umbrella-opening-vpipe.jpg) |

原生完整 MP4 保留在本机 `.local/comparisons/short-diverse-10-01/<case>-<method>/output.mp4`；
原两组位于 `.local/comparisons/short-768p-01/`。结果的 `video_asset` 与哈希可定位每条文件。
本机二十条完整视频索引：`.local/reviews/short-diverse-10-01/README.md`。视频未打包进 wheel，也未在本轮上传外部服务。

## 固定条件与证据

共同交付为 1366×768、120 帧、24fps、严格 5.000 秒、32 kHz 立体声；
实际生成 1376×768 / 124 帧，再按同一规则裁切和截尾，使用完整 H3 VAE。
计时包含新进程启动、模型加载、空提示词缓存、生成、解码、封装与最终完整声画校验；
普通 OS / Metal cache 保留，模型准备和散热等待不计入。每组固定 Ours 后 vpipe，未随机化顺序。

Ours 固定产品 `d6398c0269c13dc1aea4d10c5bcf8ee260a1e95b`，安装包与既有短片轮的 43 个运行文件逐字节相同；
普通 wheel 和模型 bundle 不变，只有输入与文档扩展，没有新算法或配方调优。
仍为 FL2VA + 官方 VSA adapter 的本地 INT8/group64 转换、既有 NAX / VSA 和加速 VAE。
Ours 去噪 MLX peak 为 33.109–33.114 GiB，这是阶段内框架峰值，不是整机峰值。

vpipe 固定未修改上游 `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` 的官方 VDN 模板、FL2VA Q8、VDN stage-dmd、Turbo v4、shift 12/3 和 i8_gemm。
八次日志均显示五步 AdaLN schedule，去噪总量最终为 250 blocks；六个配置采样点包含终点，起始进度条先显示 300 后更新为 250。
实际结构化 `actual_nfe` 未由原生程序报告，保留 null；同口径内部峰值也未报告。
双方的权重、步数、精度和引擎不同，相同 seed 不保证相同噪声，耗时差是完整系统比较。

全部十六次运行的样本记录均为接电、低电量模式关闭，温度只出现 nominal / fair，swap 增长为零；无超时或资源停止。
原始配置、逐次命令、日志、资源与视频在 `.local/comparisons/short-diverse-10-01/`；
输入冻结、完成核验、抽帧与导出脚本在 `.local/validation/short-diverse-10-01/`，相关哈希写入结果文件。
`$PRODUCT`、`$RESEARCH`、`$MODELS` 为本机路径角色，不是在线下载地址。官方 FastH3 及其权重下载仍排除在当前比较之外。

## 一键运行十条

准备 Ours/vpipe 并填写本机冻结配置后，从产品仓库执行：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json
```

该命令新建目录并执行全部二十次；本轮实际只补测新增十六次，原两组按事前方案复用。
