# 官方 FastH3 的时长对齐修复

FastVideo `a943220c115228ade5d57b3bab9a6a87fd600a10` 把对齐后的帧数除以 24，
再与 15 秒比较。H3 的时间网格要求 `17n+5` 帧，360 帧会补齐到 362 帧，因此
合法的 15 秒目标在第一次或后续重复校验时被误拒绝。

[补丁](fastvideo-h3-frame-limit.patch) 对请求和时长上下界采用相同对齐规则，允许
124–362 帧的合法模型网格，仍拒绝超出范围的请求。只修改入口几何校验；权重、
attention、步数、精度、解码和交付裁切均未改变。这里的 362 帧是模型工作量，
比较脚本仍严格交付 360 帧、15 秒声画。

## 应用与安装

在固定的上游版本建立本地分支，应用补丁并正常安装。路径按本机调整：

```bash
git -C /path/to/FastVideo switch -c codex/h3-frame-limit a943220c115228ade5d57b3bab9a6a87fd600a10
git -C /path/to/FastVideo apply --check /path/to/h3-apple/benchmarks/patches/fastvideo-h3-frame-limit.patch
git -C /path/to/FastVideo apply /path/to/h3-apple/benchmarks/patches/fastvideo-h3-frame-limit.patch
git -C /path/to/FastVideo add fastvideo/mlx_runtime/minimax_h3_pipeline.py tests/test_mlx_h3_geometry.py
git -C /path/to/FastVideo commit -m "Fix H3 aligned duration limits"
/path/to/fastvideo-env/bin/python -m pip install --force-reinstall --no-deps --no-build-isolation /path/to/FastVideo
/path/to/fastvideo-env/bin/python -I -m pytest -q /path/to/FastVideo/tests/test_mlx_h3_geometry.py
```

在 `local.json` 填入实际新 commit，保留 `local_patches` 中的补丁 SHA，重新记录
已安装 `minimax_h3_pipeline.py` 的 SHA256。比较标签使用
**Official FastH3 / VSA + frame-limit fix**；它是带明确本地补丁的官方实现。
`local.example.json` 已提供该配置。本机补丁提交为
`17825c79c4d839d03f3907769f6b19cc982ca5d4`；其他机器本地提交的哈希可以不同。

## 验证与边界

[验证记录](fastvideo-h3-frame-limit.validation.json) 绑定补丁、运行文件、wheel 和
原始测试结果。原始普通安装复现 **6 项失败、26 项通过**；补丁普通安装后
**32 项全部通过**，上游 pre-commit 检查通过。测试包括 360/362 帧、已对齐形状的
重复校验、既有合法输入、越界拒绝和内部短时序模式。

两条完整公共提示词使用真实官方 CLI，均到达
`output=1376x768x362 model=1376x768x362 audio_frames=362`，随后立即取消，进程结束，
没有发布新 MP4。这证明入口接受目标几何，不是完整生成或性能验收。

[native-three-02](../results/native-three-02/README.md) 的两次原始失败保持不变。
后续[两条完整补测](../results/fastvideo-frame-limit-01/README.md)已生成原片，但交付
时长校验失败，且后段存在坏图；没有新增成功交付耗时。入口修复的有效性与完整生成
结果分别记录，后续重测仍须使用新目录及带补丁的标签。
Ours 的日常运行核心没有因这项修复而改变。
