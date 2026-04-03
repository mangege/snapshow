# Snapshow 开发规范

## 快捷键约定

- 以 `Ctrl+字母` 为主，字母选择具有助记意义（如 `Ctrl+S` 保存、`Ctrl+G` 生成）
- `F1` 保留为帮助功能，其他 F 键不分配
- 所有快捷键必须在 Footer 中可见
- 新增快捷键时同步更新 HelpScreen 和 border title

## 代码风格

- 遵循 ruff 配置（`pyproject.toml` 中 `[tool.ruff]`）
- 行长度 120 字符
- 不写 TODO/FIXME 注释 — 要么现在修，要么记录到 issue
- 函数和类使用中文 docstring

## 模块职责

- `config.py` — 只负责配置解析和验证，不依赖其他模块
- `timeline.py` — 只负责时间线计算，纯函数，无副作用
- `voice.py` — 只负责 edge-tts 语音生成
- `video.py` — 只负责 FFmpeg 视频合成
- `tui.py` — 只负责 TUI 交互，不直接调用 FFmpeg/edge-tts
- `cli.py` — 只负责 CLI 入口编排
- `utils.py` — 跨平台工具函数（字体搜索、FFmpeg 路径、临时目录）
- `user_config.py` — 只负责用户级配置管理

## 测试策略

- 自底向上：先测 utils/config/timeline（纯函数），再测 voice/video（mock 外部依赖），最后测 TUI
- 每个公共函数至少一个测试
- 使用 pytest fixtures 共享测试数据
- 外部依赖（FFmpeg、edge-tts）必须 mock
