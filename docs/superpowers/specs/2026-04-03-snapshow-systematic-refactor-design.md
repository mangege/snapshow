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
- 添加完整公共 API 导出：
  ```python
  # Config
  from snapshow.config import ProjectConfig, SubtitleConfig, ImageConfig, VoiceConfig, SubtitleStyle
  from snapshow.config import load_config, validate_config

  # Timeline
  from snapshow.timeline import build_timeline

  # Video
  from snapshow.video import generate_video

  # Voice
  from snapshow.voice import generate_voices

  # Utils
  from snapshow.utils import find_ffmpeg, find_ffprobe, find_zh_font
  ```

---

## 第2层：核心层

### timeline.py

**改动：**
- 删除 `merge_audio_commands` 函数（未使用，实际音频合并使用 video.py 中的 `merge_audio_ffmpeg`）
- 注意：确认现有测试未引用此函数，如有则一并删除

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
   - 当前：临时修改 `segment.end` 然后恢复（ImageSegment 是 dataclass，使用属性访问）
   - 改为：在循环内创建局部变量 `adjusted_end = segment.end - transition_duration`，不修改原始数据

2. **FFmpeg 错误处理增强**
   - 当前：`subprocess.run(..., check=True, capture_output=True)` 错误时 stderr 被丢弃
   - 改为：捕获 `subprocess.CalledProcessError`，提取 stderr 并抛出带上下文的异常，包含失败的 FFmpeg 命令

3. **`_detect_gpu_encoder` 缓存**
   - 保持 `@lru_cache`（GPU 驱动运行时变化概率极低，无需 TTL 缓存）

4. **删除未使用的 `audio_dir` 创建**（video.py:353-354）
   - `audio_dir = work_dir / "audio"` 创建后从未被读取，删除此行

**测试：**
- mock FFmpeg 子进程
- 测试 GPU 检测路径（nvenc/vaapi/qsv/amf/none）
- 测试字体回退链
- 测试错误信息传递（stderr 包含在异常中）
- 测试 xfade 命令生成

### cli.py + tui.py — 临时文件管理

**改动：**

1. **创建共享工具函数**（新增至 `utils.py`）：
   ```python
   from contextlib import contextmanager
   import tempfile
   import shutil

   @contextmanager
   def temp_work_dir(prefix: str = "snapshow"):
       """上下文管理器，确保临时工作目录在退出时被清理"""
       tmp = tempfile.mkdtemp(prefix=f"{prefix}_")
       try:
           yield Path(tmp)
       finally:
           shutil.rmtree(tmp, ignore_errors=True)
   ```

2. **cli.py**：`tempfile.mkdtemp()` → 使用 `temp_work_dir()` 上下文管理器
   - 同时删除冗余音频拷贝循环（cli.py:94-101），因为 `generate_video()` 不使用 `work_dir / "audio"`

3. **tui.py `run_generation_task`**（tui.py:884, 898）：
   - 使用嵌套上下文管理器，每个临时目录独立作用域：
   ```python
   with temp_work_dir() as audio_parent:
       audio_dir = audio_parent / "audio"
       audio_dir.mkdir()
       audio_info = generate_voices(config.subtitles, audio_dir)
       # ... build timeline ...
       with temp_work_dir() as work_dir:
           # copy audio, generate video
           output_path = generate_video(config, timeline, work_dir, base_dir)
   ```
   - 注意：此方法在后台线程运行，上下文管理器的 finally 块仍会正确执行

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

**HelpScreen 同步更新：**
- `HelpScreen.compose()`（tui.py:54-78）中的帮助文本硬编码了旧快捷键
- 必须同步更新：`F3→Ctrl+R`、`F2→Ctrl+E`、`F5→Ctrl+P`、`F6→Ctrl+I`、新增 `Ctrl+Z` 撤销

**Footer 分组显示实现方案：**
- Textual 的 `Footer` 默认扁平渲染 `BINDINGS` 列表
- 使用 `Binding` 的 `priority` 参数控制显示优先级
- 分组通过 `show` 参数和 CSS 实现：在 BINDINGS 中按顺序排列，使用 `Binding` 的 `tooltip` 添加分组标签
- 替代方案：如果 Textual 版本支持，使用 `Footer` 的 `keymap` 功能；否则创建自定义 `Static` widget 替换默认 Footer
- 实际方案：保持默认 Footer，通过 BINDINGS 列表顺序和 tooltip 实现视觉分组，不创建自定义 Footer 组件（降低复杂度）

### tui.py — Bug 修复

**`action_save()` 硬编码修复**（tui.py:793-836）

当前问题：
- `fps: 30`、`width: 1080`、`height: 1920` 硬编码在 `action_save()` 中
- `voice: zh-CN-XiaoxiaoNeural` 硬编码在每个字幕条目中
- UI 中 `apply_user_config_defaults()` 使用了 `#project_fps_input`、`#project_width_input`、`#project_height_input`、`#default_voice_input` 这些 widget ID，但 `compose()` 中从未 yield 这些控件（这是一个潜在 bug）

修复步骤：
1. 在 `compose()` 的 `#controls` 区域下方新增第二行控制栏 `#controls_row2`（Horizontal），放置 4 个新 Input：
   - `Label("FPS:", id="fps_label")`
   - `Input(value="30", id="project_fps_input", width=6)`
   - `Label("宽:", id="width_label")`
   - `Input(value="1080", id="project_width_input", width=6)`
   - `Label("高:", id="height_label")`
   - `Input(value="1920", id="project_height_input", width=6)`
   - `Label("语音:", id="voice_label")`
   - `Input(value="zh-CN-XiaoxiaoNeural", id="default_voice_input", width=20)`
2. 添加 CSS `#controls_row2`：`height: 3; background: $surface; border-top: solid $panel; layout: horizontal; padding: 0 1;`，与 `#controls` 样式一致
3. 同步更新 `load_initial_config()`（tui.py:617-655），从加载的 config 中读取 fps/width/height 和 voice 填充到新 Input 控件：
   - `project = config.get("project", {})` → 读取 `project.get("fps", 30)` 等
   - 从第一个 subtitle 的 `voice.voice` 读取默认语音
4. 在 `action_save()` 中从这些控件读取值，带错误处理：
   ```python
   try:
       fps = int(self.query_one("#project_fps_input", Input).value or 30)
   except ValueError:
       fps = 30
   try:
       width = int(self.query_one("#project_width_input", Input).value or 1080)
   except ValueError:
       width = 1080
   try:
       height = int(self.query_one("#project_height_input", Input).value or 1920)
   except ValueError:
       height = 1920
   voice = self.query_one("#default_voice_input", Input).value or "zh-CN-XiaoxiaoNeural"
   ```
5. 将读取的值写入 `config_dict`：
   - `config_dict["project"]["fps"] = fps`
   - `config_dict["project"]["width"] = width`
   - `config_dict["project"]["height"] = height`
   - 每个 subtitle 的 `"voice": {"voice": voice}`

### tui.py — 代码清理

- 删除重复的 `#char_limit` CSS 定义（tui.py:518-523 和 549-556）
- 修复 `ImageFileTree.filter_paths` 冗余 `[paths]` 列表推导 + 添加 mtime 排序（合并为单次编辑）：
  ```python
  def filter_paths(self, paths: list[Path]) -> list[Path]:
      filtered = [
          p for p in paths
          if not p.name.startswith(".") and (
              p.is_dir() or p.suffix.lower() in {".jpg", ".jpeg", ".png"}
          )
      ]
      return sorted(filtered, key=lambda p: p.stat().st_mtime, reverse=True)
  ```
- 删除 `run_generation_task` 中的冗余音频拷贝循环（tui.py:901-906），因为 `generate_video()` 不使用 `work_dir / "audio"`

### tui.py — 布局优化

1. **文件树排序**：按修改时间排序（最近修改的图片排前面）
   - 实现方案：在 `ImageFileTree.filter_paths()` 中排序 `paths` 参数（公共 API），按 `path.stat().st_mtime` 降序
   - 不重写 `reload()` 或使用 `_load_directory()` 等私有 API，避免 Textual 版本升级后不兼容
   - 风险注意：`stat()` 调用在大量文件时可能有性能影响，但图片目录通常文件数有限

2. **预览列表时间戳**：每个 segment 预览显示时间范围（如 `00:00 - 00:05`）
   - 当前 `refresh_preview()`（tui.py:750-766）使用估算时长 `len(seg) * 0.25 + 0.5`
   - 改为：累积计算当前图片内每个 segment 的起止时间（从 00:00 开始），格式化为 `MM:SS - MM:SS`
   - 注意：这是相对当前图片的估算值，不跨图片累积（跨图片需要状态跟踪，留作后续扩展）
   - 实现代码：
     ```python
     current_time = 0.0
     for i, seg in enumerate(segments):
         est_duration = len(seg) * 0.25 + 0.5
         start_mmss = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
         current_time += est_duration
         end_mmss = f"{int(current_time // 60):02d}:{int(current_time % 60):02d}"
         item = ListItem(
             Static(f"[b]{i + 1}.[/][segment-text] {seg} [/] [segment-meta]({start_mmss} - {end_mmss})[/]"),
             classes="segment-item",
         )
         self.preview_list.append(item)
     ```

3. **侧栏收起**：当前 `watch_sidebar_hidden()`（tui.py:563-567）已设置 `sidebar.display = not sidebar_hidden`
   - 验证实际行为：如果 margin/padding 仍占空间，添加 CSS `sidebar_pane: { margin: 0; padding: 0; }` 配合 `display: none`
   - 如果当前行为已正确，此项跳过

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

## 第4层 TUI 测试策略

- **快捷键验证**：使用 `async with app.run_test() as pilot` 发送按键事件，验证对应 action 被调用
- **action_save() 输出**：使用 mock 文件系统，验证保存的 YAML 包含正确的 fps/width/height/voice 值
- **侧栏切换**：验证 `display` 属性变化和焦点转移行为
- **文件树排序**：验证 `reload()` 后节点按 mtime 降序排列
- **预览时间戳**：验证 `refresh_preview()` 生成的 ListItem 包含正确的时间范围格式
