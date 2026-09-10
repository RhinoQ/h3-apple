# 模型准备

先阅读 [MiniMax-H3 模型条款](../licenses/MiniMax-H3.txt)。代码的 Apache-2.0 许可证
不会改变模型和输出的地区、用途及分发条件。固定版本的官方协议排除美国、欧盟、
英国和韩国，并规定模型分发与商业使用条件；超出协议授权范围时需另行取得授权。
[官方协议原文](https://huggingface.co/MiniMaxAI/MiniMax-H3/blob/bfc8ed0353f5a9733be73e6b2c98ec0948195b86/LICENSE)
是适用条件的来源。本项目没有把模型权重放进 Git 或 Python wheel。

## 第一次准备

```bash
h3 models prepare --plan
h3 models prepare
```

`--plan` 会验证可复用文件，显示逐项来源、去重后的缺失字节数、缓存和目标盘的
额外空间需求。它不下载模型。源清单固定为公开的 MiniMax FL2VA 分区与官方
FastH3 VSA adapter，不下载 Ref2VA 或其他无关模型。

完全没有缓存时约下载 **139.11 GiB**，保留原始源文件和转换结果共约 **171 GiB**；
还需预留约 2 GiB 准备余量，生成时至少 20 GiB 可用空间。最终生成 bundle 的逻辑
大小约 93.7 GiB，其中组件与源缓存可共享同一文件内容。这些数值不能简单相加。
跨文件系统会产生真实拷贝，准确增量以本机 `--plan` 为准。

超过 20 GB 时命令会在下载前停下。确认计划后，由使用者明确授权：

```bash
h3 models prepare --allow-large-download
```

下载通过固定 revision、长度和 SHA256 校验；断点续传只请求缺失部分。
源缓存默认在 `~/Models/.h3-apple-sources`，生成 bundle 在 `~/Models/h3-apple`。
可用 `--cache-dir`、`--model-dir` 指定其他卷；`H3_MODEL_DIR` 设置日常默认模型目录。
转换在独立工作进程中运行，完成后原子发布整个 bundle。

## 已有下载或已转换模型

已有官方原始文件时，可重复传入目录。支持仓库 snapshot 根目录、FL2VA 目录和
adapter snapshot；也会检查标准 Hugging Face 缓存：

```bash
h3 models prepare --reuse-dir /path/to/MiniMax-H3/FL2VA --reuse-dir /path/to/FastH3-LoRA --plan
h3 models prepare --reuse-dir /path/to/MiniMax-H3/FL2VA --reuse-dir /path/to/FastH3-LoRA
```

所有复用内容都以完整 SHA256 验证，文件名相同不足以证明相同。相同文件系统用
硬链接，跨卷拷贝后重新验证；删除旧源文件名不会破坏新 bundle。两个名字指向同一
文件时，修改任一名字仍会改变内容，因此把准备后的模型当作只读资产使用。

已有匹配的 MLX FastH3 VSA INT8/group64 checkpoint 和完整组件目录，也可直接导入：

```bash
h3 models prepare --checkpoint /path/to/dit --components /path/to/components --model-dir /path/to/new-bundle
```

组件目录需包含 `text_encoder/`、`tokenizer/`、`vae/`、`audio_vae/`。导入记录真实
内容身份；未提供的原始 converter 来源会标为未知，不推断与某个官方 student 完全等价。

## 检查与恢复

```bash
h3 models status
h3 models verify
```

`status` 检查清单身份、文件尺寸与修改时间，`verify` 再对全部文件计算 SHA256。
再次执行 `prepare` 会识别已完成 bundle 并返回，不重复转换。已有 bundle 不会
被覆盖；更新模型或转换方式时使用新目录，验证后再切换 `H3_MODEL_DIR`。

源文件下载中断会保留带 SHA256 的 `.partial` 文件。重试继续下载；服务器未履行
Range 请求、文件损坏或大小变化时明确报错，避免静默重新下载全部内容。
保留或移走问题文件后重新查看 `--plan`。失败转换保留唯一工作目录与日志，旧现场
不会覆盖；成功转换清理自身临时输出，保留准备计划与转换凭据。

## 版本与转换身份

固定文件清单在 [model-sources.json](../src/h3_apple/data/model-sources.json)。
bundle v2 的身份绑定文件内容、源 revision、adapter、转换器源码、精度、量化、
调度缓存和后端设置。已有 v1 内容清单仍可读取。

本版从原始 MiniMax 参数合并官方 rank-64 VSA adapter，计算四步调度所需的 AdaLN
表，再保存 affine INT8/group64 DiT 与完整 FP32 VideoVAE。它不是对完整 student
snapshot 逐字节等价的声明。

转换阶段固定使用 MLX 的 `applegpu_g16s` 架构选择以复现已验证的 pre-NAX 缓存
舍入；物理机器仍是 M5。生成进程明确恢复真实 GPU 架构，继续使用 M5 NAX 加速。
这避免为转换再安装第二套 MLX。精确复现证据见 [验证记录](validation.md)。
