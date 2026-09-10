# H3 Apple

在 Apple Silicon Mac 上，从自由提示词生成带立体声音频的视频。社区项目，基于
MiniMax-H3、FastVideo 和已有的 Apple GPU 优化；与官方项目无隶属关系。

默认原生 **768p / 15 秒 / 24fps**，可选 576p 和 5–15 秒。首个实测平台为
**M5 Max / 128 GiB / macOS 26.6.1**；本版使用 M5 专属算子，其他 M 系列尚不支持。
独立包已完成真实生成与数值迁移验证，当前为发布前开发版，原生 768p 三方比较仍在验收。

## 生成第一条视频

安装 ARM64 Conda，在本仓库执行：

```bash
./install.sh
conda activate "$PWD/.local/envs/h3"
h3 models prepare --plan
h3 models prepare
h3 generate --prompt "A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell." --output bakery.mp4
```

完全无缓存约需 139.11 GiB 模型下载；超过 20 GB 时，查看计划后需显式加
`--allow-large-download`。已有文件可以 `--reuse-dir` 复用。本项目遵循
[MiniMax-H3 独立模型条款](licenses/MiniMax-H3.txt)，请在准备模型前阅读适用地区和用途条件。

结果是 MP4 与相邻的 `.run.json`，记录真实尺寸、seed、耗时、版本与模型身份；
已有文件不会覆盖。Ctrl-C 可取消。需要更小的首次检查，可加 `--resolution 576p --duration 5`。

```python
from h3_apple import generate

result = generate("A quiet bakery opens at dawn. Soft birdsong and a gentle doorbell.", seed=87001)
print(result.video_path)
print(result.elapsed_seconds)
```

[完整安装说明](docs/install.md) · [模型下载、复用与恢复](docs/models.md) ·
[CLI / Python 参数](docs/api.md) · [可运行 Python 例子](examples/generate.py)

## 当前验证与效果

在独立 Conda 环境、普通安装 wheel、研究仓库之外，已完成五秒 576p 自由提示词声画
生成；另一次完整十五秒 576p 迁移回归的 25 组张量逐字节一致，包含四步去噪、
完整解码前像素与原始立体声音频。原始权重也已由独立转换器重建为相同的有效模型。
这些是可用性与迁移证据，不把工程重构记作新的提速成果。

完整证据与适用边界见 [验证记录](docs/validation.md)。公开 motion graphics / bakery
原生 768p 视频、同规格耗时表和完整声画评审在首轮三方比较后补齐。

## 与其他入口比较

| 入口 | 本项目中的用途 | 安装与配方 |
| --- | --- | --- |
| FastH3 / Ours | 日常生成和候选优化的稳定基线 | 本仓库安装；四步 VSA、NAX 稀疏算子、完整 VAE |
| 官方 FastH3 / VSA | 直接上游参照 | 独立官方 FastVideo 环境；保留官方计算实现 |
| vpipe / VDN | 另一套 Mac 生成方案参照 | 独立原生程序；固定一套官方 VDN 配方 |

准备外部项目一次后，一条命令顺序运行三个入口 × 两个完整提示词：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py
```

比较脚本是可选工具，普通生成不依赖外部项目。输入、配置与资源停止条件见
[比较说明](benchmarks/README.md)。未测方法不因此更差；不同系统的完整耗时差额
不能全部归因于某个算子。当前官方 FastVideo 的 15 秒对齐限制须如实记录。

## 继续改进

产品拥有唯一稳定运行核心，研究仓库用固定产品 commit 开展 Proposal，通过验收后
把候选分支直接合入本仓库。参见 [开发与研究协作](docs/development.md)。
不包含长视频、参考图、Web 服务或训练功能。

自有代码 Apache-2.0；第三方源码、模型及标定材料保留各自条件，见
[来源和许可证](THIRD_PARTY_NOTICES)。模型、大日志和原始研究结果不进入 Git。
