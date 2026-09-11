# 成片比较

按用户实际交付时长选择范围：

| 交付 | 套件 | 默认比较 |
| --- | --- | --- |
| 768p / 5 秒 | `suites/motion-bakery-5s.json` | Ours、官方 FastH3 MLX / INT6 Dense、vpipe / VDN |
| 768p / 15 秒 | `suites/motion-bakery.json` | Ours、vpipe / VDN |

短片提示词事前改写为五秒内的动作，不直接截取十五秒叙事。两套均固定 motion graphics /
seed 2026 和 bakery / seed 87001，完整文本和 SHA256 由套件记录。它们是公共输入及其
改写，不用于泛化或独立盲测结论。短片准备与本机权重可用性见
[short-768p-01](results/short-768p-01/README.md)。

`compare.py` 直接调用三个现有 CLI。普通生成用户只需安装 Ours；评测脚本不安装、升级或下载其他项目。日常优化主要在研究仓库比较 Ours 候选与稳定版，发布比较或相关上游更新时才运行完整三方。

已完成的首轮新原生比较见 [native-three-02 结果](results/native-three-02/README.md)：
六次尝试、四条完整声画视频、两次官方入口规格拒绝；人工质量接受仍待完成。
对齐修复后的[官方两条补测](results/fastvideo-frame-limit-01/README.md)也已结束：
原片已生成，但两次均在交付时长校验处失败，且发现后段坏图，无成功交付成绩。

## 使用

1. [安装 Ours](../docs/install.md)，使用 `h3 models prepare` 下载/转换，或复用已有模型。
2. 按下方链接准备本轮需要的外部项目，记录具体 commit、模型来源和转换结果。
3. 复制 `local.example.json` 为不入 Git 的 `local.json`，填写绝对解释器/二进制、模型路径、固定 commit 和文件清单的 SHA256。

从产品仓库执行：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py

# 五秒三路比较
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/motion-bakery-5s.json --preflight
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/motion-bakery-5s.json
```

一轮按提示词顺序执行独立进程：十五秒四次，五秒六次。只需配置所选路线；十五秒
不要求安装官方 FastH3。Ours 命令中的 `{resolution}`、`{duration}` 从套件读取，避免
更换套件后仍运行旧时长。每轮创建唯一目录，默认在 `.local/comparisons/`，输出
`results.json`、CSV、Markdown 表，以及命令、配置、日志、媒体和资源记录。
失败耗时不进入速度表。重跑创建新目录，也可用 `--output /absolute/new/directory` 指定。

`--methods ours fastvideo` 可用于排查指定入口；这类部分运行应按实际覆盖范围描述。`Ctrl-C` 终止本轮及当前进程组，并保存取消状态。

## 固定的外部来源

2026-09-09 核对的版本：

| 入口 | commit | 一次性准备 |
| --- | --- | --- |
| FastVideo MLX | `a943220c115228ade5d57b3bab9a6a87fd600a10` | [官方 Apple Silicon 安装、模型与 MLX 转换说明](https://github.com/hao-ai-lab/FastVideo/blob/a943220c115228ade5d57b3bab9a6a87fd600a10/docs/getting_started/installation/mps.md) |
| vpipe | `0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d` | [官方构建说明](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/README.md#build-from-source)、[H3 模型准备](https://github.com/tgo-app-dev/vpipe/blob/0982c8a7b44df38142f58d8cc7bc6afdf3c2e47d/docs/MINIMAX-H3.md) |

两个版本均已完成本机独立安装或构建。vpipe 的短片试运行、交付适配检查与两条
完整原生 768p 生成已通过；各次实际状态、耗时和边界见上方结果。

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

新的五秒官方路线采用其[公开 INT6 Dense 配方](https://huggingface.co/FastVideo/FastVideo-FastH3-4-step-Preview-v1-Dense-DataFree-MLX-INT6)：
Preview v1 Dense DataFree、四步、affine INT6 / group64、BF16 激活、完整 FP32 H3 VAE。
使用未修改的 `examples/inference/basic/mlx_fasth3.py`，关闭 VSA、`fast` 和
`fast-spatial`。官方公开成片是 832×480 / 124 帧；本轮改为 1376×768 / 124 帧，必须在
本机重新验收。不要把现有 VSA adapter 权重重新标成官方 Dense 权重。

模型卡中的下载命令包含原始 transformer；已经取得可用的官方 MLX 导出时，只需
补齐共享组件。下载前核对真实文件清单和本地可复用内容，不能只依据模型卡估计流量。

两个完整公共 prompt 的原始独立官方 CLI 调用已验证：该版本将 362 / 24 算作 15.08 秒，
在加载大模型前拒绝这项规格。记录失败及不支持原因；不把 Ours 的时长修复移入
官方入口后仍称为未修改基线。此结果不代表其他时长或版本也不可用。

历史十五秒测试使用过[时长补丁](patches/README.md)，结果保留原标签和原始失败。
五秒的 124 帧在官方原始时长范围内，本轮不使用该补丁，也不继续比较官方十五秒。

vpipe 固定使用官方 `docs/pipelines/minimax-h3-vdn.vpipeline`。脚本只替换文本、seed、
套件对应的模型尺寸和帧数、输出路径及本地模型键；步骤、VDN 分支、Turbo adapter、
shift、量化等保持模板配置。配置中的六步不等同于实际 NFE，不能从名称推测。
VDN 是事前选择的官方方案，不代表所有 vpipe 配方的最优成绩。

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

共同交付为 1366×768、24fps、32 kHz 立体声：五秒交付 120 帧，模型生成 1376×768 /
124 帧；十五秒交付 360 帧，模型生成 1376×768 / 362 帧。外部入口保留原始 MP4，
再只做居中裁切与截尾；无放大、插帧或时域降采样。Ours 在自身生成 API 中完成裁切
与截尾。外部二次封装成本包含在用户等待中，并保存具体命令。五秒、十五秒各自成表。

原始 MP4 的 AAC 终点允许相对原生视频有至多一个 packet 的正负舍入，但音频必须
覆盖完整目标交付时长。短于交付或相差超过一个 packet 时直接失败，不补静音。
最终成片仍严格校验音视频时长和零起点。旧失败记录不因修复而追认为通过。

计时从启动新进程前开始，到输出通过完整声画解码、尺寸、帧数、帧率、声道和时长检查后结束。包含首次加载、编译、空提示词缓存、生成和封装；正常系统和 Metal cache 保留。准备与等待 AC/nominal 起跑条件的时间单独记录。当前运行开始要求接电、关闭低电量模式、nominal；运行中遇到严重温度、超过 2 GiB swap 增长、剩余磁盘不足 20 GiB 或超时会终止并保留证据。

Ours 由工作进程持有设备锁；两个外部 CLI 由比较脚本持锁。所有并发 H3 调度都需要遵循同一锁约定。已存在的外部非合作 GPU 任务不能仅凭文件锁自动发现。

脚本会把当前评测 Conda 环境的 FFmpeg 路径提供给子命令，并记录实际二进制身份。
仅指定绝对 Python 路径不会激活 Conda 的命令搜索路径，这一步不能省略。停止任务
时先发 Ctrl-C 信号，使 Ours CLI 有机会关闭它的独立 GPU 工作进程，超时再强制停止。

每条结果的人工质量审查初始为 `pending`。机器媒体通过不代表质量通过。观看完整声画后，质量结论应保存在研究记录并链接这些不可覆盖的结果；一次六任务运行只用于描述观察，不自动证明稳定提速、质量胜出或跨内容泛化。
