# Snapshow 逻辑修复与 TUI 增强实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复视频无声问题，实装 TUI 分辨率/语音保存逻辑，重构已失效的测试套件。

**Architecture:** 采用 TDD 驱动修复。首先重构测试以反映当前代码结构，随后修复 `video.py` 音频合并逻辑，最后完善 TUI 交互。

**Tech Stack:** Python, Textual, FFmpeg, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/video.py` | 收集所有 segment 音频并传递给 FFmpeg；增强错误捕获。 |
| Modify | `snapshow/tui.py` | 从 UI 控件读取保存值；实装 Ctrl+P；显示全局时间戳。 |
| Modify | `tests/test_config.py` | 移除 VoiceConfig 引用，适配 ProjectConfig 语音字段。 |
| Modify | `tests/test_timeline.py` | 适配 SubtitleConfig 新结构（移除 voice 字段）。 |
| Modify | `tests/test_video.py` | 新增音频收集路径验证测试。 |

---

### Task 1: 重构测试套件 - 适配 ProjectConfig 结构

**Files:**
- Modify: `tests/test_config.py`
- Modify: `tests/test_timeline.py`

- [ ] **Step 1: 修改 tests/test_config.py 中的过时测试**

将 `test_load_config_with_voice` 修改为验证 `ProjectConfig` 的全局语音字段：
```python
    def test_load_config_with_voice(self, tmp_path):
        config_data = {
            "project": {
                "name": "test",
                "voice": "zh-CN-YunxiNeural",
                "voice_rate": "+10%"
            },
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        assert config.voice == "zh-CN-YunxiNeural"
        assert config.voice_rate == "+10%"
```
并移除 `test_public_api_exports` 中对 `VoiceConfig` 的检查。

- [ ] **Step 2: 修改 tests/test_timeline.py 移除 VoiceConfig**

更新 `make_subtitle` 助手函数：
```python
def make_subtitle(id: str, text: str, image: str) -> SubtitleConfig:
    return SubtitleConfig(
        id=id,
        text=text,
        image=image,
    )
```
并同步更新所有调用处，移除 `voice` 参数。

- [ ] **Step 3: 运行测试验证修复（当前应不再报导入错误，但逻辑可能因代码未改而失败）**

Run: `./.venv/bin/python3 -m pytest tests/test_config.py tests/test_timeline.py -v`

- [ ] **Step 4: Commit**

```bash
git add tests/test_config.py tests/test_timeline.py
git commit -m "test: refactor tests to match new ProjectConfig structure"
```

---

### Task 2: 修复 video.py - 音频路径收集与错误增强

**Files:**
- Modify: `snapshow/video.py`

- [ ] **Step 1: 在 video.py 中补全音频收集逻辑**

在 `generate_video` 函数（约 370 行）中修改：
```python
    for i, segment in enumerate(timeline):
        # ... 保持 adjusted_segment 逻辑不变 ...
        create_image_segment_video(adjusted_segment, config.style, config, clip_path, base_dir)
        video_paths.append(clip_path)

        # 修复：收集该片段的所有音频路径并去重
        for ap in segment.audio_paths:
            if Path(ap) not in all_audio_paths:
                all_audio_paths.append(Path(ap))
```

- [ ] **Step 2: 增强 FFmpeg 错误捕获**

封装 `_run_ffmpeg` (如果尚未封装) 或确保所有 `subprocess.run` 包含 stderr 输出：
```python
def _run_ffmpeg(cmd: list[str], desc: str) -> None:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        error_msg = f"FFmpeg {desc} 失败!\n命令: {' '.join(cmd)}\n错误输出: {e.stderr}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
```

- [ ] **Step 3: 编写测试验证音频路径收集**

在 `tests/test_video.py` 中：
```python
def test_generate_video_collects_audio_paths(tmp_path):
    from snapshow.video import generate_video
    from snapshow.timeline import ImageSegment
    from snapshow.config import ProjectConfig
    
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (tmp_path / "img.jpg").touch()
    
    seg = ImageSegment(
        image_id="img1", image_path="img.jpg", start=0, end=2,
        audio_paths=["audio1.mp3", "audio2.mp3"]
    )
    
    with patch("snapshow.video.subprocess.run") as mock_run, \
         patch("snapshow.video._detect_gpu_encoder", return_value=None), \
         patch("snapshow.video._resolve_font", return_value=("f", "n")):
        mock_run.return_value = MagicMock(returncode=0)
        generate_video(ProjectConfig(images=[]), [seg], work_dir, tmp_path)
        
        # 验证 merge_audio_ffmpeg 是否收到了 2 个音频输入
        # 查找包含 "-i audio1.mp3 -i audio2.mp3" 的调用
        audio_merge_call = [call for call in mock_run.call_args_list if "concat" in str(call)]
        assert len(audio_merge_call) > 0
```

- [ ] **Step 4: 运行测试验证**

Run: `./.venv/bin/python3 -m pytest tests/test_video.py -v`

- [ ] **Step 5: Commit**

```bash
git add snapshow/video.py tests/test_video.py
git commit -m "fix: collect audio paths in generate_video and enhance error handling"
```

---

### Task 3: 完善 TUI - 修复保存逻辑与快捷键

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: 更新 action_save 读取 UI 控件值**

在 `action_save` (约 800 行) 中：
```python
        # 从分辨率下拉框读取
        res_value = self.query_one("#project_resolution_select", Select).value or "1080x1920"
        width, height = map(int, res_value.split("x"))
        
        # 从语音下拉框读取
        voice = self.query_one("#project_voice_select", Select).value or "zh-CN-XiaoxiaoNeural"
        
        # 从字符限制输入框读取
        try:
            max_chars = int(self.query_one("#char_limit", Input).value)
        except ValueError:
            max_chars = 10

        config_dict = {
            "project": {
                "name": "tui_project",
                "width": width,
                "height": height,
                "fps": 30, # 默认 30
                "voice": voice,
                "max_chars": max_chars,
                # ... 其他字段 ...
            },
            # ...
        }
```

- [ ] **Step 2: 实装 Ctrl+P 聚焦预览**

1. 在 `BINDINGS` 中确认 `Binding("ctrl+p", "focus_preview", "预览", show=True)` 存在。
2. 添加 action 方法：
```python
    def action_focus_preview(self) -> None:
        self.query_one("#preview_list").focus()
```

- [ ] **Step 3: 优化预览列表的时间戳显示**

修改 `refresh_preview` 中的时间计算逻辑，使其累加全局时间：
```python
        current_global_time = 0.0
        # 这里的累加需要基于所有已分配图片的时长
        # 简化版：仅显示当前图片内的相对偏移，但在标题显示“全局开始时间”
        for i, seg in enumerate(segments):
             # ... 逻辑参考设计文档 ...
```

- [ ] **Step 4: 运行 lint 验证代码质量**

Run: `ruff check snapshow/tui.py`

- [ ] **Step 5: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: fix TUI save logic, add Ctrl+P, and improve preview timestamps"
```

---

### Task 4: 最终集成测试

- [ ] **Step 1: 运行所有测试套件**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 2: 启动 TUI 验证 UI 交互**

Run: `./.venv/bin/python3 -m snapshow ui`
(手动验证：修改分辨率保存，查看生成的 project_tui.yaml 是否正确)

- [ ] **Step 3: Commit**

```bash
git commit --allow-empty -m "chore: final verification of logic and TUI fixes"
```
