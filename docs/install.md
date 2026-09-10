# 安装与第一条视频

首个实测平台是 Apple M5 Max / 128 GiB / macOS 26.6.1。本版算子要求 M5，
至少 96 GiB 统一内存与 macOS 26.2；96 GiB 机器尚无完整端到端验证。
生成前至少保留 20 GiB 可用磁盘，实际模型准备需要更多空间。建议接电运行。

## Conda 环境

先安装 ARM64 的 [Miniforge](https://github.com/conda-forge/miniforge) 或已有的 Conda。
在取得的仓库根目录执行：

```bash
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 --version
```

安装器使用可读的 [环境定义](../environments/environment.yml) 及
[osx-arm64 精确锁](../environments/conda-osx-arm64.lock)，创建私有 Conda 缓存和环境；
Python 3.11.15、MLX 0.32.0、FFmpeg 8.1.2 及 Python 依赖由锁文件固定。
实际安装普通 wheel。不会修改系统 Python 或用户级 site-packages。
无需 PyTorch，也无需准备外部比较项目。

脚本或调度器使用固定解释器，不依赖当前 shell 是否激活：

```bash
"$PWD/.local/envs/h3/bin/python" -m h3_apple --version
```

MLX 的同一版本有不同平台 wheel。安装器明确使用 macOS 26 后端，`doctor` 会核对
实际加载的动态库；仅有相同的 `pip freeze` 版本号不足以替代这项检查。

## 模型与离线生成

模型准备方式、缺失下载量、转换峰值与恢复方法见 [模型准备](models.md)。
准备完成后运行：

```bash
h3 doctor
h3 generate --prompt "A paper boat drifts across a quiet pond. Soft water sounds and birdsong." --output boat.mp4
```

默认输出原生 768p、15 秒、24fps 的完整声画视频。想先检查环境，可明确选择较小工作量：

```bash
h3 generate --prompt "A paper boat drifts across a quiet pond. Soft water sounds and birdsong." --resolution 576p --duration 5 --seed 123 --output boat-smoke.mp4
```

`doctor` 在模型未准备好时返回非零并提示 `h3 models prepare`；这是可执行的缺项提示。
生成阶段设置 Hugging Face 与 Transformers 离线模式，不会临时下载缺失组件。

## 故障恢复

- `conda` 不可用：先完成 Conda 安装，或将 `CONDA_EXE` 指向其绝对可执行路径。
- 模型缺失：执行模型准备；已有下载可通过 `--reuse-dir` 登记。
- 后端不匹配：重新执行 `./install.sh`，不要只手工替换一个动态库。
- 设备被占用：等待当前 H3 任务结束。统一设备锁默认在 `~/.cache/h3-apple/device.lock`。
- 资源保护停止：查看 `.run.json` 和日志，释放空间/内存或等待散热后用新输出路径重试。
- 安装或下载中断：重跑安装命令或模型准备命令；保留错误日志，损坏文件不会当作完整资产使用。

`H3_MODEL_DIR` 只更改模型目录，`H3_DEVICE_LOCK` 可指定所有合作任务共同使用的锁路径。
无需修改 Metal 或线程环境变量。详细参数见 [API](api.md)。
