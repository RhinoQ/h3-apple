# H3 Apple

在 Apple Silicon Mac 上，从自由提示词生成带立体声音频的视频。社区项目，基于
MiniMax-H3、FastVideo 和已有的 Apple GPU 优化；与官方项目无隶属关系。

默认原生 **768p / 15 秒 / 24fps**，可选 576p 和 5–15 秒。首个实测平台为
**M5 Max / 128 GiB / macOS 26.6.1**；本版使用 M5 专属算子，其他 M 系列尚不支持。
独立安装、模型重建、真实生成与数值迁移验证均已完成。当前为 `0.1.0.dev0` 开发预览；
已有 15 秒和 5 秒共八条成片通过用户人工声画评价，见
[验收记录](benchmarks/reviews/existing-eight-20260911.json)。五秒比较已完成十条提示词，
新增十六条通过媒体检查；另完成两条新增十五秒场景、共四条视频。
这些新增视频的人工质量评价待完成。

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

## 效果与等待时间

M5 Max / 128 GiB，原生 768p、15 秒完整声画视频。以下为固定公共输入的单次观察：

| 入口 | motion graphics | bakery |
| --- | ---: | ---: |
| FastH3 / Ours | 36 分 47 秒 | 33 分 18 秒 |
| vpipe / VDN | 41 分 15 秒 | 39 分 30 秒 |

同一台机器的 **768p / 5 秒**比较，完整十条提示词、每项每个系统各一次：

| 覆盖 | Ours 平均等待 | vpipe 平均等待 | Ours 等待减少 |
| --- | ---: | ---: | ---: |
| 新增八组 | 5 分 57 秒 | 9 分 09 秒 | 35.1% |
| 全部十组（含既有两组） | 5 分 56 秒 | 9 分 07 秒 | 34.8% |

计时包含新进程启动、模型加载、生成、封装与完整声画检查。十组均为 Ours 等待更短；
这不是重复测量的稳定倍率或质量胜出结论。原两组短片已获用户声画接受，新增十六条
仍待人工评价；Ours 营地多主体、vpipe 蘑菇形态问题已随[十提示词结果](benchmarks/results/short-diverse-10-01/README.md)记录。
[十五秒结果](benchmarks/results/native-three-02/README.md)与
[原两组五秒结果](benchmarks/results/short-768p-01/README.md)分别记录输入、固定版本和配方。
另完成[古书密钥、月地晶花两组十五秒比较](benchmarks/results/cinematic-two-15s-01/README.md)，
四条均成功交付；独立成表，沿用现有运行核心与模型。
当前两个时长都只比较 Ours / vpipe；官方 FastH3 对照已取消，历史
[失败补测](benchmarks/results/fastvideo-frame-limit-01/README.md)保留供复核。
[两条可播放示例](examples/README.md)

[![Motion graphics 实际生成预览](examples/previews/motion-graphics-ours.jpg)](examples/previews/motion-graphics-ours.mp4)

[![Bakery 实际生成预览](examples/previews/bakery-ours.jpg)](examples/previews/bakery-ours.mp4)

点击缩略图播放 360p 小预览，保留完整 15 秒声画；耗时对应原生 768p 成片。
这是不同固定配方的系统观察，不宣称新的算法提速或总体质量胜出。

63 项快速测试通过；独立安装后在研究仓库之外完成自由提示词生成，完整 576p
迁移回归的 25 组张量逐字节一致，另有原生形状前向、模型重建和真实 GPU 取消验证。
具体证据与适用边界见 [验证记录](docs/validation.md)。

## 与其他入口比较

| 入口 | 本项目中的用途 | 安装与配方 |
| --- | --- | --- |
| FastH3 / Ours | 日常生成和候选优化的稳定基线 | 本仓库安装；四步 VSA、NAX 稀疏算子、完整 VAE |
| vpipe / VDN | 另一套 Mac 生成方案参照 | 独立原生程序；固定一套官方 VDN 配方 |

准备 vpipe 后，一条命令运行两个场景；十五秒和五秒都比较 Ours / vpipe：

```bash
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/motion-bakery-5s.json
# 完整十条五秒提示词
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/diverse-10-5s.json
# 两条新增十五秒提示词
"$PWD/.local/envs/h3/bin/python" benchmarks/compare.py --suite benchmarks/suites/cinematic-two-15s.json
```

比较脚本是可选工具，普通生成不依赖外部项目。输入、配置与资源停止条件见
[比较说明](benchmarks/README.md)。未测方法不因此更差；不同系统的完整耗时差额
不能全部归因于某个算子。首次比较前可加 `--preflight` 检查所选路线的准备状态。
新增八个场景的来源、计划和状态由[十提示词比较](benchmarks/results/short-diverse-10-01/README.md)维护。

## 继续改进

产品拥有唯一稳定运行核心，研究仓库用固定产品 commit 开展 Proposal，通过验收后
把候选分支直接合入本仓库。参见 [开发与研究协作](docs/development.md)。
不包含长视频、参考图、Web 服务或训练功能。

自有代码 Apache-2.0；第三方源码、模型及标定材料保留各自条件，见
[来源和许可证](THIRD_PARTY_NOTICES)。模型、大日志和原始研究结果不进入 Git。
