# 三方比较

比较 **FastH3 / Ours、官方 FastH3 / VSA、vpipe / VDN**。两个完整公共提示词为 motion graphics / seed 2026 和 bakery / seed 87001；文本和 SHA256 由 `suites/motion-bakery.json` 固定。两者均为已见输入，不用于新的泛化结论。

`compare.py` 直接调用三个现有 CLI。普通生成用户只需安装 Ours；评测脚本不安装、升级或下载其他项目。日常优化主要在研究仓库比较 Ours 候选与稳定版，发布比较或相关上游更新时才运行完整三方。

## 使用

1. [安装 Ours](../docs/install.md)，使用 `h3 models prepare` 下载/转换，或复用已有模型。
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

两个版本均已完成本机独立安装或构建。vpipe 的短片试运行与交付适配检查已经通过；
完整原生 768p 三方结果仍在验收，具体状态以结果文件为准。

FastVideo 的一次性安装示例，路径按本机调整：

```bash
git clone https://github.com/hao-ai-lab/FastVideo.git /path/to/FastVideo
git -C /path/to/FastVideo checkout a943220c115228ade5d57b3bab9a6a87fd600a10
conda create --yes --copy --prefix /path/to/fastvideo-env -c conda-forge python=3.12 pip
/path/to/fastvideo-env/bin/python -m pip install '/path/to/FastVideo[mlx]'
/path/to/fastvideo-env/bin/python -m pip check
```

模型准备采用链接的官方 MLX 转换说明。也可显式复用与其 checkpoint 格式兼容的
本地转换资产，但必须在 `weights` 中说明 base/adapter/转换器，不能把它写成未验证
的完整 student 权重。先核对规格支持情况，再决定是否值得下载额外大权重。

FastVideo 使用其 `examples/inference/basic/mlx_fasth3.py`，启用 VSA，关闭 `fast` 和 `fast-spatial`，使用完整 FP32 VideoVAE。示例保留官方推荐的 `auto` attention 实现；该版本中它是 reference 路径。使用其他明确支持的实现时，必须在正式开跑前固定，并在结果中完整标明。不能按不同提示词分别选择最快配置。

该官方源码的时长检查按对齐后的帧数计算；362 / 24 超过 15 秒。目标 15 秒交付是否可用，必须先验证。如官方入口拒绝，记录失败/不支持，不把 Ours 的时长修复移入官方入口后仍称为未修改基线。

vpipe 固定使用官方 `docs/pipelines/minimax-h3-vdn.vpipeline`。脚本只替换文本、seed、1376×768 / 362 帧、输出路径和本地模型键；步骤、VDN 分支、Turbo adapter、shift、量化等保持模板配置。配置中的六步不等同于实际 NFE，不能从名称推测。VDN 是首版事前选择的官方方案，不代表所有 vpipe 配方的最优成绩。

本机构建可使用官方 `VPIPE_METAL_RUNTIME_COMPILE=ON`，免除额外 Metal 工具链下载。依赖子模块固定在该 commit；独立 Conda 环境提供 CMake、Ninja 和 FFmpeg 头文件。CLI 的 CMake target 名是 `vpipe-cli`，产物是 `build/apps/vpipe/vpipe`。通过 `VPIPE_FFMPEG_DIR` 指向匹配头文件 ABI 的 Conda `lib` 目录。vpipe 从启动目录读取 `session.json` 和模型 registry，因此 `cwd` 必须是准备好的工作目录。

构建步骤（需要已安装的 Apple Command Line Tools）：

```bash
git clone https://github.com/tgo-app-dev/vpipe.git /path/to/vpipe
git -C /path/to/vpipe checkout 0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d
git -C /path/to/vpipe submodule update --init --recursive
conda create --yes --copy --prefix /path/to/vpipe-build-env -c conda-forge cmake ninja ffmpeg=8.1.2
/path/to/vpipe-build-env/bin/cmake -S /path/to/vpipe -B /path/to/vpipe-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM=/path/to/vpipe-build-env/bin/ninja -DCMAKE_PREFIX_PATH=/path/to/vpipe-build-env -DVPIPE_BUILD_PYTHON=OFF -DVPIPE_BUILD_MACOS_APP=OFF -DVPIPE_METAL_RUNTIME_COMPILE=ON
/path/to/vpipe-build-env/bin/cmake --build /path/to/vpipe-build --target vpipe-cli
```

在新的工作目录里沿用官方准备流程；已有模型可用原生注册 stage 登记，避免重复下载：

```bash
VPIPE_FFMPEG_DIR=/path/to/vpipe-build-env/lib /path/to/vpipe-build/apps/vpipe/vpipe --launch-stage model-register --stage-cfg model_dir=/path/to/complete-q8-model --stage-cfg key=local/MiniMax-H3-FL2VA-8bit
```

同样登记 VDN 为 `OpenVDN/vdn-minimax-h3-stage-dmd`、Turbo adapter 为
`larryvrh/MiniMax-H3-Turbo-Lora-v4-600-ema`，与固定官方模板对应。
不要复制或硬链接旧工作目录的可写 LMDB；仅复用经过校验的模型文件。

## 资产与可追溯性

模型准备成本不计入生成时间，已有文件应优先复用。每个 `asset_receipts` 项引用一份准备时已做完整 SHA256 校验的 JSON 清单，脚本在计时外校验清单自身 SHA256，再核对每个模型文件的大小和修改时间。Ours 的 `bundle.json` 可直接使用；外部资产采用如下格式，文件路径相对清单所在目录，或相对 `asset_receipts` 中指定的 `root`：

```json
{"files": [{"path": "models/example.safetensors", "size": 123, "mtime_ns": 1234567890000000000, "sha256": "真实的完整文件SHA256"}]}
```

必须记录原始 base、adapter、量化/转换器和环境。原生 MiniMax base 融合官方 adapter 的本地转换不等同于完整 student snapshot，表中应明确这个边界。最新官方运行时与 Ours 的上游基点不同，则整段耗时差是系统比较，不能全归因于 Ours 的优化。

`runtime_files` 可另外绑定实际安装的 Python 文件、MLX 动态库/metallib，以及
vpipe dylib 的 `{path, sha256}`。正式配置同时核对安装文件与 source commit；
只检查一个源码目录或一个很小的 CLI 可执行文件，不足以代表它实际加载的运行时。

## 共同计时与结果边界

默认交付 1366×768、360 帧、15 秒、24fps、32 kHz 立体声，实际模型生成 1376×768 / 362 帧。外部入口保留原始 MP4，再只做居中裁切与截尾；无放大、插帧或时域降采样。Ours 在自身生成 API 中完成裁切与截尾。外部二次封装的成本包含在用户等待中，并保存具体 FFmpeg 命令。这是完整系统比较，不是相同编码次数的算子消融。

原始官方 MP4 允许至多一个 AAC packet 的额外尾部填充，供随后截尾；最终成片仍严格
校验音视频时长和零起点。这处理编码封装的尾部边界，不放宽最终交付要求。

计时从启动新进程前开始，到输出通过完整声画解码、尺寸、帧数、帧率、声道和时长检查后结束。包含首次加载、编译、空提示词缓存、生成和封装；正常系统和 Metal cache 保留。准备与等待 AC/nominal 起跑条件的时间单独记录。当前运行开始要求接电、关闭低电量模式、nominal；运行中遇到严重温度、超过 2 GiB swap 增长、剩余磁盘不足 20 GiB 或超时会终止并保留证据。

Ours 由工作进程持有设备锁；两个外部 CLI 由比较脚本持锁。所有并发 H3 调度都需要遵循同一锁约定。已存在的外部非合作 GPU 任务不能仅凭文件锁自动发现。

每条结果的人工质量审查初始为 `pending`。机器媒体通过不代表质量通过。观看完整声画后，质量结论应保存在研究记录并链接这些不可覆盖的结果；一次六任务运行只用于描述观察，不自动证明稳定提速、质量胜出或跨内容泛化。
