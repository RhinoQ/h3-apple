# 两条新增十五秒场景比较

2026-09-11，古书密钥与月地晶花分别完成 Ours / vpipe VDN 生成，四次尝试全部成功，
没有重试或按输出挑选提示词、种子。四条均通过完整声画解码与交付规格检查；
**新增视频的人工声画质量评价仍为 pending**，先前八条视频的接受不延伸到本轮。

| 场景 | seed | Ours 等待 | vpipe 等待 | Ours 等待减少 |
| --- | ---: | ---: | ---: | ---: |
| 古书密钥 | 15011 | 24 分 52 秒 | 29 分 27 秒 | 15.5% |
| 月地晶花 | 15012 | 25 分 31 秒 | 29 分 46 秒 | 14.3% |
| 本轮两组平均 | — | 25 分 12 秒 | 29 分 36 秒 | 14.9% |

百分比由未取整秒数计算；汇总为两套系统总等待的差额除以 vpipe 总等待。
本轮只扩展输入，运行核心与模型沿用原基线。不同提示词的绝对耗时不同，不能把相对
[原两组十五秒](../native-three-02/README.md)的时间变化解释为新的代码提速。
每个输入、每套系统仅一次，固定先 Ours 后 vpipe；这些是系统观察，不证明稳定倍率、
某个算法的独立收益或质量胜出，也不与五秒结果合并。

## 输入与计时

完整英文提示词、官方写作来源及改写归属见
[两条提示词](../../prompts/cinematic-two-15s/README.md)，输入和种子由
[套件](../../suites/cinematic-two-15s.json)固定；[事前方案](plan.json)先于生成创建。
古书密钥覆盖人物、手部、道具与短对白；月地晶花覆盖全身行走、前景遮挡、开花及运镜。

实测为 Apple M5 Max / 128 GiB / macOS 26.6.1。
共同交付为 **1366×768、15.000 秒、360 帧、24fps、32 kHz 立体声**；
原生模型生成 1376×768 / 362 帧，按既定交付逻辑居中裁切与截尾。
计时从启动独立新进程前至完整声画和规格校验通过，包含加载、生成与封装。
准备和等待降温不计入；保留正常系统/Metal cache，提示词缓存为空。
四次均接电、低电量关闭，监控温度为 nominal/fair、swap 增长为零，没有触发停止条件。

Ours 两次均实际执行 4 NFE、200 次直接稀疏 attention，零 fallback。
vpipe 沿用官方 VDN 模板，未导出可直接比较的结构化 NFE，本轮保持该字段为空；
不把配置中的步骤数当作测得 NFE。两系统的权重、adapter、精度与采样配方分别固定，
并不相同；具体配置见结果中的 `weights` 和 `recipe`。

## 抽帧观察

每条检查首尾及均匀抽取的 12 帧。这是知道方法身份的静态检查，没有连续播放或听音，
不能代替盲评、声画同步与完整十五秒的质量验收。四条抽样帧未见整体坏图。

| 视频 | 观察及待复核项 |
| --- | --- |
| [古书密钥 / Ours](diagnostics/archive-discovery-ours.jpg) | 打开书本、举钥匙和转头可辨认；镜头推进至近景，末段有多次朝向变化。手指、动作连续性、对白和音效待复核。 |
| [古书密钥 / vpipe](diagnostics/archive-discovery-vpipe.jpg) | 打开书本、举钥匙与末段转头可辨认；光线较暗、镜头缓慢推进。暗部细节、手部和钥匙连续性、对白及音效待复核。 |
| [月地晶花 / Ours](diagnostics/lunar-flower-walk-ours.jpg) | 行走、停步、抬手、花瓣展开及彩色光带可辨认；前景晶体偶有遮挡，结尾人物上半身保留在下缘。连续脚印、步态、开花运动与音效待复核。 |
| [月地晶花 / vpipe](diagnostics/lunar-flower-walk-vpipe.jpg) | 行走、停步、抬手、花瓣展开及地面光带可辨认；前景花茎偶有遮挡，结尾人物上半身保留在下缘。连续脚印、人物/花瓣运动与音效待复核。 |

## 可复核证据

[results.json](results.json) 是完整成绩、媒体检查、哈希、资源与抽帧观察的权威导出；
[results.csv](results.csv) 提供四次尝试的简表。原始失败和成功记录均不覆盖。

- 实际计时源码 commit：`6f68563e1a7c8b76fe5187b8906dabedf25f313e`；之后提交只补结果与文档。
- 安装和源码一致的 43 个运行文件 SHA256：`9151e26d4683b235a8eee422f508723a9846a9718c7ace4009a3984a1e4de9ac`。
- 模型身份：`6b2716e05fd19c8d554a609bc97e46ef29c504e81f1798b02008ea003670b942`。
- vpipe 固定版本：`0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d`。
- 原始证据：产品仓库 `.local/comparisons/cinematic-two-15s-01/`，逐条保留 MP4、命令、配置、日志和资源记录。
- 独立检查：`.local/validation/cinematic-two-15s-01/`，保留准备、14 项相关测试、完成记录、媒体哈希复核与抽帧证据。
- 本地完整视频索引：`.local/reviews/cinematic-two-15s-01/README.md`。这些本机路径不是公开下载链接。

复现使用套件和当前固定环境，结果必须写入新目录：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json
```
