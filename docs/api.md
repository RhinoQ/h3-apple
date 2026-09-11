# 生成接口

CLI 与 Python 调用同一个 `generate()`；普通用户只选择 Ours 的稳定配方。
每次生成启动独立工作进程，退出后释放模型内存。没有常驻服务。

```python
from h3_apple import generate, resolve

request = resolve("A quiet bakery opens at dawn. Gentle bells and birdsong.", seed=87001)
print(request.to_dict())  # 不加载 MLX 或模型

result = generate(
    prompt="A quiet bakery opens at dawn. Gentle bells and birdsong.",
    resolution="768p",
    duration=15,
    seed=87001,
    output="bakery.mp4",
    on_progress=lambda event: print(event),
)
print(result.video_path)
print(result.metadata_path)
print(result.elapsed_seconds)
```

| Python 参数 | CLI | 行为 |
| --- | --- | --- |
| `prompt` / `prompt_file` | `--prompt` / `--prompt-file` | 必须二选一，完整 UTF-8 文本；可以使用任意提示词 |
| `preset="ours"` | `--preset ours` | 当前唯一稳定配方；版本与代码、模型身份一同记录 |
| `resolution="768p"` | `--resolution 768p` | 可选 `768p`、`576p` |
| `duration=15` | `--duration 15` | 5–15 秒，必须对应 24fps 的整数帧数 |
| `seed=None` | `--seed 87001` | 未提供时自动生成并记录；允许 0–4294967295 |
| `output=None` | `--output bakery.mp4` | 默认创建唯一输出目录；指定路径时旁写 `bakery.run.json`，拒绝覆盖 |
| `model_dir=None` | `--model-dir /path` | 默认 `$H3_MODEL_DIR`，未设置时为 `~/Models/h3-apple` |
| `on_progress=None` | 自动打印到 stderr | 回调收到阶段与去噪/解码进度的小字典；stdout 保留最终 JSON |
| `timeout=7200` | `--timeout 7200` | 超时终止整个进程组，保留失败记录 |
| `diagnostics=False` | `--diagnostics` | 研究用逐步张量、原始像素与音频；体积大且增加用户等待 |

`GenerationResult` 返回 `video_path`、`metadata_path`、`elapsed_seconds` 和 `seed`。
`GenerationRequest` 是冻结的数据类，可调用 `to_dict()` 查看实际规格。
API 导出 `generate`、`resolve`、`GenerationRequest`、`GenerationResult`。

## 交付与实际计算规格

| 请求 | MP4 交付 | 模型实际生成 |
| --- | --- | --- |
| 768p / 15 秒 | 1366×768，360 帧 | 1376×768，362 帧 |
| 768p / 5 秒 | 1366×768，120 帧 | 1376×768，124 帧 |
| 576p / 15 秒 | 1024×576，360 帧 | 1024×576，362 帧 |
| 576p / 5 秒 | 1024×576，120 帧 | 1024×576，124 帧 |

统一 24fps、32 kHz 立体声。按固定方式居中裁切、截取请求帧数与音频时长；
不会放大或插帧。步数、shift、VSA 和 VAE 组合归配方管理，不作为日常调参接口。
API 接受的规格范围与已完成的硬件验证范围分开记录，详见 [验证记录](validation.md)。

```bash
h3 resolve --prompt-file prompt.txt --resolution 768p --duration 15 --seed 42
h3 generate --prompt-file prompt.txt --output runs/example.mp4
```

## 取消与错误

CLI 按 Ctrl-C；Python 可捕获 `KeyboardInterrupt`。取消和超时会停止工作进程组，
释放设备锁。失败的 `.run.json` 与隐藏工作目录中的日志保留，可从错误信息定位。
重新运行使用新输出路径，先查看旧失败现场。普通成功生成只保留 MP4 和小型运行记录；
诊断模式额外保留张量目录。

无效请求在加载模型前拒绝。已有输出文件、模型被改动、设备被另一任务占用、
不支持的硬件、媒体验证失败会报告明确错误，不会用另一种配方静默回退。
同一模型根目录按只读资产使用；修改权重后应在新目录重新准备。
