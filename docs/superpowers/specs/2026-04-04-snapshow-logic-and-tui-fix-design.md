# Snapshow 逻辑修复与 TUI 交互增强设计文档

> 日期：2026-04-04
> 状态：待实现
> 目标：修复视频无声、TUI 保存失效及测试断层问题

## 1. 核心逻辑修复 (Core Logic)

### 1.1 `video.py` 音频路径收集补全
- **问题**：`generate_video` 虽定义了 `all_audio_paths`，但未填充，导致合成视频无声。
- **改动**：
    - 在 `generate_video` 的循环中，遍历 `segment.audio_paths` 并将其添加到 `all_audio_paths` 总列表中。
    - **去重逻辑**：确保来自同一图片的不同字幕片段（共享同一音频文件）只被添加一次，避免 FFmpeg 合成时出现音频重叠或长度错误。

### 1.2 FFmpeg 错误上下文增强
- **改动**：在 `video.py` 中，统一封装 `subprocess.run`。当发生 `CalledProcessError` 时，捕获 `e.stderr`，并在抛出的 `RuntimeError` 中包含失败的完整命令和错误详情。

## 2. TUI 数据流与交互优化 (TUI & UX)

### 2.1 完善 TUI 数据闭环
- **读取 UI 控件**：更新 `action_save` 方法，从 `project_resolution_select`（分辨率下拉框）获取宽/高，从 `project_voice_select` 获取语音引擎设置。
- **状态同步**：确保 `load_initial_config` 和 `apply_user_config_defaults` 能够正确将 YAML 中的配置映射到对应的 Select 控件上。

### 2.2 交互增强
- **Ctrl+P (Focus Preview)**：实装 `action_focus_preview` 方法，通过快捷键直接聚焦右下角的“分段预览”列表。
- **时间戳显示**：在“分段预览”的 ListItem 中，显示该字幕片段在整个项目时间线中的全局起止时间（格式：`MM:SS - MM:SS`）。

### 2.3 异常可视化
- 在 `run_generation_task` 失败时，利用 `self.notify(str(e), severity="error")` 将 FFmpeg 或 Python 层的错误直接反馈给用户。

## 3. 测试套件重构 (Test Suite)

### 3.1 适配新数据结构
- **移除 VoiceConfig**：在 `tests/test_config.py` 和 `tests/test_timeline.py` 中删除所有对 `VoiceConfig` 的引用。
- **配置适配**：将语音相关的 `voice`, `voice_rate` 等字段直接定义在 `ProjectConfig` 对象中，确保测试代码与重构后的 `config.py` 逻辑对齐。

### 3.2 新增验证用例
- **音频合并验证**：在 `tests/test_video.py` 中 Mock `subprocess.run`，验证 `generate_video` 是否正确输出了包含所有音频路径的 `all_audio_paths`。
- **公共 API 校验**：在 `tests/test_config.py` 中确保 `snapshow` 包导出的 API 不再包含已删除的 `VoiceConfig`。

## 4. 实施顺序

1. **测试先行**：修改 `tests/` 目录下的过时用例，使其在当前代码下报错更明确（针对结构而非导入）。
2. **逻辑修复**：在 `video.py` 中补全音频收集逻辑，并通过新增测试。
3. **TUI 适配**：更新 `tui.py` 的保存与加载逻辑，实装 `Ctrl+P`。
4. **最终验证**：运行全量测试并启动 TUI 进行端到端验证。
