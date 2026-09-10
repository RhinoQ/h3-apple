# 三方比较

比较 **FastH3 / Ours、官方 FastH3 / VSA、vpipe / VDN**。两个完整公共提示词为 motion graphics / seed 2026 和 bakery / seed 87001；文本和 SHA256 由 `suites/motion-bakery.json` 固定。两者均为已见输入，不用于新的泛化结论。

`compare.py` 直接调用三个现有 CLI。普通生成用户只需安装 Ours；评测脚本不安装、升级或下载其他项目。日常优化主要在研究仓库比较 Ours 候选与稳定版，发布比较或相关上游更新时才运行完整三方。

## 使用

1. 安装 Ours，复用已准备好的模型。目前 `models prepare` 需显式提供 `--checkpoint` 和 `--components`；默认下载及转换入口仍在实现。
2. 按下方链接准备两个官方项目，记录具体 commit、模型来源和转换结果。
3. 复制 `local.example.json` 为不入 Git 的 `local.json`，填写绝对解释器/二进制、模型路径、固定 commit 和文件清单的 SHA256。

从产品仓库执行：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py
```

一轮按提示词顺序执行六个独立进程。每轮创建唯一目录，默认在 `.local/comparisons/`，输出 `results.json`、CSV、带视频链接的 Markdown 表，以及每次的命令、配置、日志、媒体和资源记录。失败保留原因，不能把失败退出的时间排入速度表。重复运行会创建新目录；也可以用 `--output /absolute/new/directory` 明确指定新目录。

`--methods ours fastvideo` 可用于排查指定入口；这类部分运行应按实际覆盖范围描述。`Ctrl-C` 终止本轮及当前进程组，并保存取消状态。

## 固定的外部来源

2026-09-09 核对的版本：

| 入口 | commit | 一次性准备 |
| --- | --- | --- |
| FastVideo MLX | `a943220c115228ade5d57b3bab9a6a87fd600a10` | [官方 Apple Silicon 安装、模型与 MLX 转换说明](https://github.com/hao-ai-lab/FastVideo/blob/a943220c115228ade5d57b3bab9a6a87fd600a10/docs/getting_started/installation/mps.md) |
| vpipe | `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` | [官方构建说明](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/README.md#build-from-source)、[H3 模型准备](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/docs/MINIMAX-H3.md) |

这两个版本的安装及本机运行仍在验收。具体结果以生成的结果文件为准，不能把本节当作两个方法已完成端到端验证的声明。

FastVideo 使用其 `examples/inference/basic/mlx_fasth3.py`，启用 VSA，关闭 `fast` 和 `fast-spatial`，使用完整 FP32 VideoVAE。示例保留官方推荐的 `auto` attention 实现；该版本中它是 reference 路径。使用其他明确支持的实现时，必须在正式开跑前固定，并在结果中完整标明。不能按不同提示词分别选择最快配置。

该官方源码的时长检查按对齐后的帧数计算；362 / 24 超过 15 秒。目标 15 秒交付是否可用，必须先验证。如官方入口拒绝，记录失败/不支持，不把 Ours 的时长修复移入官方入口后仍称为未修改基线。

vpipe 固定使用官方 `docs/pipelines/minimax-h3-vdn.vpipeline`。脚本只替换文本、seed、1376×768 / 362 帧、输出路径和本地模型键；步骤、VDN 分支、Turbo adapter、shift、量化等保持模板配置。配置中的六步不等同于实际 NFE，不能从名称推测。VDN 是首版事前选择的官方方案，不代表所有 vpipe 配方的最优成绩。

本机构建可使用官方 `VPIPE_METAL_RUNTIME_COMPILE=ON`，免除额外 Metal 工具链下载。依赖子模块固定在该 commit；独立 Conda 环境提供 CMake、Ninja 和 FFmpeg 头文件。CLI 的 CMake target 名是 `vpipe-cli`，产物是 `build/apps/vpipe/vpipe`。通过 `VPIPE_FFMPEG_DIR` 指向匹配头文件 ABI 的 Conda `lib` 目录。vpipe 从启动目录读取 `session.json` 和模型 registry，因此 `cwd` 必须是准备好的工作目录。

## 资产与可追溯性

模型准备成本不计入生成时间，已有文件应优先复用。每个 `asset_receipts` 项引用一份准备时已做完整 SHA256 校验的 JSON 清单，脚本在计时外校验清单自身 SHA256，再核对每个模型文件的大小和修改时间。Ours 的 `bundle.json` 可直接使用；外部资产采用如下格式，文件路径相对清单所在目录，或相对 `asset_receipts` 中指定的 `root`：

```json
{"files": [{"path": "models/example.safetensors", "size": 123, "mtime_ns": 1234567890000000000, "sha256": "真实的完整文件SHA256"}]}
```

必须记录原始 base、adapter、量化/转换器和环境。原生 MiniMax base 融合官方 adapter 的本地转换不等同于完整 student snapshot，表中应明确这个边界。最新官方运行时与 Ours 的上游基点不同，则整段耗时差是系统比较，不能全归因于 Ours 的优化。

## 共同计时与结果边界

默认交付 1366×768、360 帧、15 秒、24fps、32 kHz 立体声，实际模型生成 1376×768 / 362 帧。外部入口保留原始 MP4，再只做居中裁切与截尾；无放大、插帧或时域降采样。Ours 在自身生成 API 中完成裁切与截尾。外部二次封装的成本包含在用户等待中，并保存具体 FFmpeg 命令。这是完整系统比较，不是相同编码次数的算子消融。

计时从启动新进程前开始，到输出通过完整声画解码、尺寸、帧数、帧率、声道和时长检查后结束。包含首次加载、编译、空提示词缓存、生成和封装；正常系统和 Metal cache 保留。准备与等待 AC/nominal 起跑条件的时间单独记录。当前运行开始要求接电、关闭低电量模式、nominal；运行中遇到严重温度、超过 2 GiB swap 增长、剩余磁盘不足 20 GiB 或超时会终止并保留证据。

Ours 由工作进程持有设备锁；两个外部 CLI 由比较脚本持锁。所有并发 H3 调度都需要遵循同一锁约定。已存在的外部非合作 GPU 任务不能仅凭文件锁自动发现。

每条结果的人工质量审查初始为 `pending`。机器媒体通过不代表质量通过。观看完整声画后，质量结论应保存在研究记录并链接这些不可覆盖的结果；一次六任务运行只用于描述观察，不自动证明稳定提速、质量胜出或跨内容泛化。
