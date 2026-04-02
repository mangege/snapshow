# Snapshow 系统性重构设计文档

> 日期：2026-04-03
> 状态：待实现
> 方法：分层递进式（方案 A）

## 概述

对 snapshow 项目进行系统性重构，修复已知 bug、清理未使用代码、统一快捷键风格、优化 TUI 布局，并建立自底向上的测试骨架和开发规范。

## 重构分层

```
第5层 ── 规范层          (快捷键约定、公共API、文档)
         ↑
第4层 ── 交互层          (TUI快捷键统一、save修复、布局优化)
         ↑
第3层 ── 合成层          (video.py bug修复、错误处理、临时文件管理)
         ↑
第2层 ── 核心层          (timeline清理、voice.py ffprobe修复)
         ↑
第1层 ── 基础层          (utils、config、user_config修复 + 测试)
```

---

## 第1层：基础层

### config.py

**改动：**
- 删除 `SubtitleConfig.render` 字段（定义于 config.py:27，从未被读取或使用）
- 验证逻辑保持不变

**测试：**
- 扩展现有 7 个测试
- 新增边界情况：空配置、缺失必填字段、非法值类型

### user_config.py

**改动：**
- 无代码逻辑改动
- 确保 XDG 合规性（当前已使用 `Path.home()/.config/snapshow/`）

**测试：**
- `test_init`：首次初始化创建默认配置
- `test_load`：读取已有配置
- `test_save`：保存后文件内容正确
- `test_xdg_compliance`：路径符合 XDG 规范

### utils.py

**改动：**
- 无代码改动（当前逻辑正确）

**测试：**
- `test_find_ffmpeg`：mock 各平台路径
- `test_find_ffprobe`：mock 各平台路径
- `test_find_zh_font`：mock Windows/macOS/Linux 字体路径

### `__init__.py`

**改动：**
- 添加公共 API 导出：
  ```python
  from snapshow.config import ProjectConfig, SubtitleConfig, ImageConfig, VoiceConfig, SubtitleStyle
  from snapshow.config import load_config, validate_config
  ```

---

## 第2层：核心层

### timeline.py

**改动：**
- 删除 `merge_audio_commands` 函数（未使用，实际音频合并使用 video.py 中的 `merge_audio_ffmpeg`）

**测试：**
- 扩展现有 6 个测试
- 新增边界情况：空字幕列表、时间重叠、零持续时间图像

### voice.py

**改动：**
- `get_audio_duration` 中硬编码 `"ffprobe"` 改为使用 `from snapshow.utils import find_ffprobe`
- 当前代码（voice.py 中）：`subprocess.run(["ffprobe", ...], ...)` 
- 改为：`ffprobe_path = find_ffprobe()` 然后使用 `ffprobe_path`

**测试：**
- mock edge-tts 调用
- mock ffprobe 调用，验证使用 `find_ffprobe()` 返回的路径

---

## 第3层：合成层

### video.py

**改动：**

1. **segment.end 突变修复**（video.py:361-374）
   - 当前：临时修改 `segment["end"]` 然后恢复
   - 改为：在循环内创建局部变量 `adjusted_end = segment["end"] - transition_duration`，不修改原始数据

2. **FFmpeg 错误处理增强**
   - 当前：`subprocess.run(..., check=True, capture_output=True)` 错误时 stderr 被丢弃
   - 改为：捕获 `subprocess.CalledProcessError`，提取 stderr 并抛出带上下文的异常，包含失败的 FFmpeg 命令

3. **`_detect_gpu_encoder` 缓存**
   - 保持 `@lru_cache`（GPU 驱动运行时变化概率极低，无需 TTL 缓存）

**测试：**
- mock FFmpeg 子进程
- 测试 GPU 检测路径（nvenc/vaapi/qsv/amf/none）
- 测试字体回退链
- 测试错误信息传递（stderr 包含在异常中）
- 测试 xfade 命令生成

### cli.py

**改动：**

1. **临时文件泄漏修复**
   - 当前：`tempfile.mkdtemp()` 创建临时目录但从未清理
   - 改为：使用 `tempfile.TemporaryDirectory()` 配合 `with` 语句，或 `try/finally` 确保清理

---

## 第4层：交互层

### tui.py — 快捷键统一

**原则：统一 Ctrl 组合，F 键只保留系统级功能（F1 帮助）**

| 功能 | 当前 | 新方案 | 说明 |
|------|------|--------|------|
| 退出 | `Ctrl+Q` | `Ctrl+Q` | 不变 |
| 保存 | `Ctrl+S` | `Ctrl+S` | 不变 |
| 生成 | `Ctrl+G` | `Ctrl+G` | 不变 |
| 帮助 | `F1` | `F1` | 系统级，保留 |
| 切换主题 | `Ctrl+T` | `Ctrl+T` | 不变 |
| 切换侧栏 | `Ctrl+B` | `Ctrl+B` | 不变 |
| 用户配置 | `Ctrl+U` | `Ctrl+U` | 不变 |
| 预览配置 | `F3` | `Ctrl+R` | Review |
| 聚焦编辑器 | `F2` | `Ctrl+E` | Edit |
| 聚焦预览列表 | `F5` | `Ctrl+P` | Preview |
| 聚焦侧栏文件树 | `F6` | `Ctrl+I` | fIle tree |
| 撤销 | _(无)_ | `Ctrl+Z` | 新增（利用 TextArea 内置 undo） |

**Footer 分组显示：**
- 文件：`Ctrl+S` 保存 | `Ctrl+G` 生成 | `Ctrl+Q` 退出
- 编辑：`Ctrl+E` 编辑器 | `Ctrl+Z` 撤销
- 导航：`Ctrl+P` 预览 | `Ctrl+I` 文件树
- 视图：`Ctrl+T` 主题 | `Ctrl+B` 侧栏 | `Ctrl+R` 配置 | `Ctrl+U` 设置 | `F1` 帮助

### tui.py — Bug 修复

**`action_save()` 硬编码修复**（tui.py:793）
- 当前：硬编码 `fps: 30`、`width: 1080`、`height: 1920`、`voice: zh-CN-XiaoxiaoNeural`
- 改为：从 UI 控件读取：
  - `self.fps_input.value`
  - `self.width_input.value`
  - `self.height_input.value`
  - `self.voice_select.value`

### tui.py — 代码清理

- 删除重复的 `#char_limit` CSS 定义（tui.py:518-523 和 549-556）
- 修复 `ImageFileTree.filter_paths` 冗余 `[paths]` 列表推导（tui.py:414-417）

### tui.py — 布局优化

1. **文件树排序**：按修改时间排序（最近修改的图片排前面）
2. **预览列表时间戳**：每个 segment 预览显示时间范围（如 `00:00 - 00:05`）
3. **侧栏收起完全隐藏**：确保 `sidebar_pane` 收起时不占布局空间（使用 `display: none` 而非仅隐藏内容）

---

## 第5层：规范层

### `docs/CONVENTIONS.md`

**内容：**
- 快捷键命名约定（Ctrl+字母为主，助记优先，F1 保留给帮助）
- 代码风格（遵循 ruff，无 TODO 注释需及时清理）
- 模块职责边界（config 只管配置，video 只管合成，timeline 只管调度）
- 测试策略（自底向上，纯函数优先，外部依赖用 mock）

### `pyproject.toml`

**改动：**
- 添加 pytest 脚本配置
- 确保 ruff 配置完整

---

## 实施顺序

1. 第1层：基础层修复 + 测试
2. 第2层：核心层修复 + 测试
3. 第3层：合成层修复 + 测试
4. 第4层：交互层修复 + 测试
5. 第5层：规范文档

每层完成后独立提交，方便回滚。
