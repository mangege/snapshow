# Snapshow 系统性重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复已知 bug、清理未使用代码、统一快捷键为 Ctrl 组合、优化 TUI 布局，并建立自底向上的测试骨架。

**Architecture:** 分层递进式（方案 A）— 从基础层到规范层逐层推进，每层完成后独立提交。

**Tech Stack:** Python 3.10+, Click, Textual, edge-tts, FFmpeg, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/utils.py` | Add `temp_work_dir()` context manager |
| Modify | `snapshow/config.py` | Delete `SubtitleConfig.render` field |
| Modify | `snapshow/__init__.py` | Add public API exports |
| Modify | `snapshow/timeline.py` | Delete `merge_audio_commands` |
| Modify | `snapshow/voice.py` | Fix hardcoded ffprobe → `find_ffprobe()` |
| Modify | `snapshow/video.py` | Fix segment mutation, error handling, dead code |
| Modify | `snapshow/cli.py` | Fix temp file leak, remove dead audio copy |
| Modify | `snapshow/tui.py` | Shortcuts, save bug, layout, code cleanup |
| Modify | `snapshow/user_config.py` | No code changes (test only) |
| Create | `tests/test_utils.py` | Utils module tests |
| Create | `tests/test_user_config.py` | User config tests |
| Create | `tests/test_voice.py` | Voice module tests |
| Create | `tests/test_video.py` | Video module tests |
| Create | `tests/test_tui.py` | TUI interaction tests |
| Modify | `tests/test_config.py` | Expand config tests |
| Modify | `tests/test_timeline.py` | Expand timeline tests |
| Create | `docs/CONVENTIONS.md` | Development conventions |
| Modify | `pyproject.toml` | Add pytest config |

---

### Task 1: Layer 1 — utils.py + temp_work_dir

**Files:**
- Modify: `snapshow/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing test for temp_work_dir**

```python
# tests/test_utils.py
import os
from pathlib import Path
from snapshow.utils import temp_work_dir

def test_temp_work_dir_creates_and_cleans_up():
    dir_path = None
    with temp_work_dir() as tmp:
        dir_path = tmp
        assert tmp.is_dir()
        (tmp / "test.txt").write_text("hello")
    assert not dir_path.exists()  # cleaned up

def test_temp_work_dir_cleans_up_on_exception():
    dir_path = None
    try:
        with temp_work_dir() as tmp:
            dir_path = tmp
            raise ValueError("boom")
    except ValueError:
        pass
    assert not dir_path.exists()  # cleaned up even on exception

def test_temp_work_dir_custom_prefix():
    with temp_work_dir(prefix="mytest") as tmp:
        assert "mytest" in tmp.name
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_utils.py -v
```
Expected: FAIL — `temp_work_dir` not found

- [ ] **Step 3: Implement temp_work_dir in utils.py**

Add to end of `snapshow/utils.py`:

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

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_utils.py::test_temp_work_dir_creates_and_cleans_up tests/test_utils.py::test_temp_work_dir_cleans_up_on_exception tests/test_utils.py::test_temp_work_dir_custom_prefix -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snapshow/utils.py tests/test_utils.py
git commit -m "feat: add temp_work_dir context manager with tests"
```

---

### Task 2: Layer 1 — config.py cleanup + tests

**Files:**
- Modify: `snapshow/config.py:27`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Delete SubtitleConfig.render field**

In `snapshow/config.py`, remove line 27:
```python
# DELETE this line:
    render: bool = True  # 是否在画面上渲染文字
```

- [ ] **Step 2: Run existing tests to verify no regression**

```bash
pytest tests/test_config.py -v
```
Expected: All 7 tests PASS

- [ ] **Step 3: Add boundary tests to test_config.py**

Append to `tests/test_config.py`:

```python
class TestConfigEdgeCases:
    def test_config_missing_project_key(self, tmp_path):
        config_data = {
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)
        assert config.name == "output"  # default

    def test_config_missing_images_key(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)
        assert config.images == []

    def test_config_missing_subtitles_key(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)
        assert config.subtitles == []

    def test_config_invalid_fps_type(self, tmp_path):
        config_data = {
            "project": {"name": "test", "fps": "not_a_number"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        # Should not raise during load (dataclass accepts any type)
        config = load_config(config_file)
        assert config.fps == "not_a_number"  # type not enforced at load

    def test_config_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_config("/nonexistent/path/config.yaml")
```

- [ ] **Step 4: Run all config tests**

```bash
pytest tests/test_config.py -v
```
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add snapshow/config.py tests/test_config.py
git commit -m "refactor: remove unused SubtitleConfig.render, add edge case tests"
```

---

### Task 3: Layer 1 — user_config.py tests

**Files:**
- Create: `tests/test_user_config.py`

- [ ] **Step 1: Write tests for user_config**

```python
# tests/test_user_config.py
import os
from pathlib import Path
from snapshow.user_config import init_user_config, load_user_config, USER_CONFIG_PATH


def test_init_creates_config(tmp_path, monkeypatch):
    config_dir = tmp_path / ".config" / "snapshow"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    result = init_user_config(overwrite=True)
    assert result is True
    assert config_dir.exists()
    assert (config_dir / "config.yaml").exists()


def test_load_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    init_user_config(overwrite=True)
    
    config = load_user_config()
    assert "project" in config
    assert "voice" in config
    assert config["project"]["fps"] == 30
    assert config["voice"]["voice"] == "zh-CN-XiaoxiaoNeural"


def test_init_no_overwrite_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    init_user_config(overwrite=True)
    result = init_user_config(overwrite=False)
    assert result is False


def test_xdg_compliance(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    init_user_config(overwrite=True)
    expected = tmp_path / ".config" / "snapshow" / "config.yaml"
    assert USER_CONFIG_PATH == str(expected) or Path(USER_CONFIG_PATH) == expected
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_user_config.py -v
```
Expected: All 4 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_user_config.py
git commit -m "test: add user_config tests"
```

---

### Task 4: Layer 1 — __init__.py public API

**Files:**
- Modify: `snapshow/__init__.py`

- [ ] **Step 1: Write test for public API exports**

Append to `tests/test_config.py` or create new test:

```python
def test_public_api_exports():
    from snapshow import (
        ProjectConfig, SubtitleConfig, ImageConfig, VoiceConfig, SubtitleStyle,
        load_config, validate_config,
        build_timeline,
        generate_video,
        generate_voices,
        find_ffmpeg, find_ffprobe, find_zh_font,
    )
    assert callable(load_config)
    assert callable(validate_config)
    assert callable(build_timeline)
    assert callable(generate_video)
    assert callable(generate_voices)
    assert callable(find_ffmpeg)
    assert callable(find_ffprobe)
    assert callable(find_zh_font)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py::test_public_api_exports -v
```
Expected: FAIL — imports not available from `snapshow`

- [ ] **Step 3: Implement __init__.py exports**

```python
# snapshow/__init__.py
from snapshow.config import ProjectConfig, SubtitleConfig, ImageConfig, VoiceConfig, SubtitleStyle
from snapshow.config import load_config, validate_config

from snapshow.timeline import build_timeline

from snapshow.video import generate_video

from snapshow.voice import generate_voices

from snapshow.utils import find_ffmpeg, find_ffprobe, find_zh_font

__all__ = [
    "ProjectConfig", "SubtitleConfig", "ImageConfig", "VoiceConfig", "SubtitleStyle",
    "load_config", "validate_config",
    "build_timeline",
    "generate_video",
    "generate_voices",
    "find_ffmpeg", "find_ffprobe", "find_zh_font",
]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py::test_public_api_exports -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snapshow/__init__.py tests/test_config.py
git commit -m "feat: add public API exports to __init__.py"
```

---

### Task 5: Layer 2 — timeline.py cleanup

**Files:**
- Modify: `snapshow/timeline.py`
- Modify: `tests/test_timeline.py`

- [ ] **Step 1: Check if merge_audio_commands is referenced in tests**

```bash
grep -r "merge_audio_commands" tests/
```
If found, note the test names for removal.

- [ ] **Step 2: Delete merge_audio_commands from timeline.py**

Remove lines 130-143 from `snapshow/timeline.py`:
```python
# DELETE these lines:
def merge_audio_commands(timeline: list[ImageSegment], output_path: str) -> str:
    """生成 FFmpeg 合并音频的命令"""
    all_audio_paths = []
    for seg in timeline:
        all_audio_paths.extend(seg.audio_paths)

    if not all_audio_paths:
        return ""

    inputs = " ".join([f"-i '{p}'" for p in all_audio_paths])
    filter_complex = "".join([f"[{i}:a]" for i in range(len(all_audio_paths))])
    filter_complex += f"concat=n={len(all_audio_paths)}:v=0:a=1[outa]"

    return f"{inputs} -filter_complex '{filter_complex}' -map '[outa]' '{output_path}'"
```

- [ ] **Step 3: Run existing timeline tests**

```bash
pytest tests/test_timeline.py -v
```
Expected: All 6 tests PASS

- [ ] **Step 4: Add edge case tests to test_timeline.py**

Append to `tests/test_timeline.py`:

```python
class TestTimelineEdgeCases:
    def test_empty_images_list(self):
        timeline = build_timeline([], [], {}, 0.5)
        assert timeline == []

    def test_empty_subtitles_list(self):
        images = [ImageConfig(id="img1", path="test.jpg")]
        timeline = build_timeline(images, [], {}, 0.5)
        assert len(timeline) == 1
        assert timeline[0].image_id == "img1"
        assert timeline[0].end - timeline[0].start == 3.0  # default duration

    def test_title_without_audio(self):
        images = [ImageConfig(id="img1", path="test.jpg")]
        subtitles = [SubtitleConfig(id="sub1", text="hello", image="img1")]
        timeline = build_timeline(images, subtitles, {}, 0.5, title="My Title")
        # Title segment not created (no __title__ in audio_info)
        assert all(seg.image_id != "__title__" for seg in timeline)

    def test_logo_creates_black_segment(self):
        images = [ImageConfig(id="img1", path="test.jpg")]
        subtitles = [SubtitleConfig(id="sub1", text="hello", image="img1")]
        audio_info = {"sub1": (Path("audio.mp3"), 2.0)}
        timeline = build_timeline(images, subtitles, audio_info, 0.5, logo="MyLogo")
        logo_seg = [s for s in timeline if s.image_id == "__logo__"]
        assert len(logo_seg) == 1
        assert logo_seg[0].image_path == "__black__"
        assert logo_seg[0].end - logo_seg[0].start == 1.0

    def test_timeline_continuity(self):
        images = [
            ImageConfig(id="img1", path="test1.jpg"),
            ImageConfig(id="img2", path="test2.jpg"),
        ]
        subtitles = [
            SubtitleConfig(id="sub1", text="hello", image="img1"),
            SubtitleConfig(id="sub2", text="world", image="img2"),
        ]
        audio_info = {
            "sub1": (Path("audio1.mp3"), 2.0),
            "sub2": (Path("audio2.mp3"), 3.0),
        }
        timeline = build_timeline(images, subtitles, audio_info, 0.5)
        # Verify no gaps between segments
        for i in range(len(timeline) - 1):
            assert timeline[i].end == timeline[i + 1].start
```

Also need to add imports at top of test file:
```python
from snapshow.timeline import build_timeline, ImageSegment, SubtitleSegment
from snapshow.config import ImageConfig, SubtitleConfig
```

- [ ] **Step 5: Run all timeline tests**

```bash
pytest tests/test_timeline.py -v
```
Expected: All 11 tests PASS

- [ ] **Step 6: Commit**

```bash
git add snapshow/timeline.py tests/test_timeline.py
git commit -m "refactor: remove unused merge_audio_commands, add edge case tests"
```

---

### Task 6: Layer 2 — voice.py ffprobe fix

**Files:**
- Modify: `snapshow/voice.py`
- Create: `tests/test_voice.py`

- [ ] **Step 1: Read current voice.py to understand structure**

```bash
cat snapshow/voice.py
```

Note the `get_audio_duration` function and its hardcoded `"ffprobe"`.

- [ ] **Step 2: Write tests for voice module**

```python
# tests/test_voice.py
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestGetAudioDuration:
    @patch("snapshow.voice.find_ffprobe")
    def test_uses_find_ffprobe(self, mock_find_ffprobe):
        """Verify get_audio_duration uses find_ffprobe() not hardcoded string"""
        mock_find_ffprobe.return_value = "/usr/bin/ffprobe"
        
        from snapshow.voice import get_audio_duration
        
        # Mock subprocess.run
        with patch("snapshow.voice.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                stdout="1.234\n",
                returncode=0
            )
            result = get_audio_duration(Path("test.mp3"))
            
            # Verify ffprobe was called with the mocked path
            call_args = mock_run.call_args[0][0]
            assert "/usr/bin/ffprobe" in call_args[0]
            assert result == 1.234


class TestGenerateVoices:
    @patch("snapshow.voice.generate_voice")
    @pytest.mark.asyncio
    async def test_generate_voices_returns_audio_info(self, mock_generate_voice, tmp_path):
        """Test generate_voices returns correct audio_info dict"""
        mock_generate_voice.return_value = ("audio.mp3", 2.0)
        
        from snapshow.config import SubtitleConfig, VoiceConfig
        from snapshow.voice import generate_voices
        
        subtitles = [
            SubtitleConfig(id="sub1", text="hello", image="img1", voice=VoiceConfig()),
        ]
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()
        
        audio_info = await generate_voices(subtitles, audio_dir)
        
        assert "sub1" in audio_info
        assert audio_info["sub1"][1] == 2.0
```

- [ ] **Step 3: Run tests to verify current state**

```bash
pytest tests/test_voice.py -v
```
Expected: `test_uses_find_ffprobe` FAILS (current code uses hardcoded "ffprobe")

- [ ] **Step 4: Fix voice.py — replace hardcoded ffprobe**

In `snapshow/voice.py`, find `get_audio_duration` and change:

```python
# BEFORE:
def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", ...],
        ...
    )

# AFTER:
from snapshow.utils import find_ffprobe

def get_audio_duration(audio_path: Path) -> float:
    ffprobe_path = find_ffprobe()
    result = subprocess.run(
        [ffprobe_path, ...],
        ...
    )
```

- [ ] **Step 5: Run tests to verify fix**

```bash
pytest tests/test_voice.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add snapshow/voice.py tests/test_voice.py
git commit -m "fix: use find_ffprobe() instead of hardcoded ffprobe path"
```

---

### Task 7: Layer 3 — video.py fixes

**Files:**
- Modify: `snapshow/video.py`
- Create: `tests/test_video.py`

- [ ] **Step 1: Write tests for video module**

```python
# tests/test_video.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import replace
import subprocess

import pytest

from snapshow.timeline import ImageSegment, SubtitleSegment
from snapshow.config import ProjectConfig, SubtitleStyle


class TestSegmentEndMutation:
    def test_generate_video_does_not_mutate_segments(self, tmp_path):
        """Verify generate_video does not mutate original segment.end"""
        # Create a minimal timeline
        segment = ImageSegment(
            image_id="img1",
            image_path="test.jpg",
            start=0.0,
            end=2.0,
            subtitles=[],
            audio_paths=[],
        )
        original_end = segment.end
        timeline = [segment]
        
        config = ProjectConfig(
            name="test",
            fps=30,
            width=1080,
            height=1920,
            transition_duration=0.5,
        )
        
        work_dir = tmp_path / "work"
        work_dir.mkdir()
        base_dir = tmp_path
        
        # Create a dummy image file
        (tmp_path / "test.jpg").touch()
        
        # Mock all subprocess calls
        with patch("snapshow.video.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch("snapshow.video._detect_gpu_encoder", return_value=None):
                with patch("snapshow.video._resolve_font", return_value=("fontfile", "TestFont")):
                    try:
                        from snapshow.video import generate_video
                        generate_video(config, timeline, work_dir, base_dir)
                    except Exception:
                        pass  # May fail due to mocking, but we check mutation
        
        assert segment.end == original_end
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_video.py::TestSegmentEndMutation -v
```
Expected: FAIL — segment.end is mutated

- [ ] **Step 3: Fix segment.end mutation in video.py**

In `snapshow/video.py`, around lines 359-374, replace:

```python
# BEFORE:
for i, segment in enumerate(timeline):
    original_end = segment.end
    if i < len(timeline) - 1:
        segment.end += config.transition_duration

    clip_path = clips_dir / f"clip_{i:03d}.mp4"
    create_image_segment_video(segment, config.style, config, clip_path, base_dir)
    video_paths.append(clip_path)

    for sub in segment.subtitles:
        all_audio_paths.append(Path(sub.audio_path))

    segment.end = original_end

# AFTER:
from dataclasses import replace

for i, segment in enumerate(timeline):
    if i < len(timeline) - 1:
        adjusted_segment = replace(segment, end=segment.end + config.transition_duration)
    else:
        adjusted_segment = segment

    clip_path = clips_dir / f"clip_{i:03d}.mp4"
    create_image_segment_video(adjusted_segment, config.style, config, clip_path, base_dir)
    video_paths.append(clip_path)

    for sub in segment.subtitles:
        all_audio_paths.append(Path(sub.audio_path))
```

- [ ] **Step 4: Delete unused audio_dir in video.py**

Remove lines 353-354:
```python
# DELETE:
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 5: Enhance FFmpeg error handling**

In `snapshow/video.py`, find all `subprocess.run(..., check=True, capture_output=True)` calls and wrap:

```python
# BEFORE:
subprocess.run(cmd, check=True, capture_output=True, text=True)

# AFTER:
try:
    subprocess.run(cmd, check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as e:
    raise RuntimeError(
        f"FFmpeg command failed: {' '.join(cmd)}\n"
        f"stderr: {e.stderr}"
    ) from e
```

Apply to: `create_image_segment_video`, `merge_videos_with_xfade`, `merge_audio_ffmpeg`, `create_title_card_video`, `create_logo_card_video`.

- [ ] **Step 6: Run test to verify fix**

```bash
pytest tests/test_video.py::TestSegmentEndMutation -v
```
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add snapshow/video.py tests/test_video.py
git commit -m "fix: prevent segment mutation, enhance FFmpeg error handling, remove dead audio_dir"
```

---

### Task 8: Layer 3 — cli.py temp file fix

**Files:**
- Modify: `snapshow/cli.py`

- [ ] **Step 1: Fix temp file leak and remove dead audio copy**

In `snapshow/cli.py`, find the `generate` command (around lines 89-105) and replace:

```python
# BEFORE:
    logger.info("开始生成视频...")
    work_dir = Path(tempfile.mkdtemp()) / "snapshow_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 将音频拷贝到工作目录
    final_audio_dir = work_dir / "audio"
    final_audio_dir.mkdir(parents=True, exist_ok=True)
    for sub_id, (path, duration) in audio_info.items():
        import shutil

        new_path = final_audio_dir / path.name
        shutil.copy2(path, new_path)
        audio_info[sub_id] = (new_path, duration)

    output_path = generate_video(config, timeline, work_dir, base_dir)

    logger.info(f"视频生成成功: {output_path}")

# AFTER:
    logger.info("开始生成视频...")
    from snapshow.utils import temp_work_dir

    with temp_work_dir() as work_dir:
        output_path = generate_video(config, timeline, work_dir, base_dir)
        logger.info(f"视频生成成功: {output_path}")
```

Also remove unused `import tempfile` if no longer needed.

- [ ] **Step 2: Run lint**

```bash
python -m ruff check snapshow/cli.py
```

- [ ] **Step 3: Commit**

```bash
git add snapshow/cli.py
git commit -m "fix: use temp_work_dir for cleanup, remove dead audio copy in cli"
```

---

### Task 9: Layer 4 — tui.py shortcuts + HelpScreen + BINDINGS + border titles

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: Update BINDINGS list**

In `snapshow/tui.py`, update the BINDINGS list (lines 559-571):

```python
# BEFORE relevant lines:
    BINDINGS = [
        ...
        ("f3", "preview_config", "预览配置"),
        ("f2", "focus_editor", "聚焦编辑器"),
        ("f5", "focus_preview", "聚焦预览"),
        ("f6", "focus_sidebar", "聚焦文件树"),
        ...
    ]

# AFTER:
    BINDINGS = [
        ("ctrl+q", "quit", "退出"),
        ("ctrl+s", "save", "保存"),
        ("ctrl+g", "generate", "生成"),
        ("ctrl+r", "preview_config", "预览配置"),
        ("ctrl+e", "focus_editor", "聚焦编辑器"),
        ("ctrl+p", "focus_preview", "聚焦预览"),
        ("ctrl+i", "focus_sidebar", "聚焦文件树"),
        ("ctrl+z", "undo", "撤销"),
        ("ctrl+t", "toggle_theme", "切换主题"),
        ("ctrl+b", "toggle_sidebar", "切换侧栏"),
        ("ctrl+u", "user_config", "用户配置"),
        ("f1", "show_help", "帮助"),
    ]
```

- [ ] **Step 2: Add action_undo method**

Add after existing action methods:

```python
def action_undo(self):
    self.text_area.undo()
```

- [ ] **Step 3: Update HelpScreen compose()**

In `HelpScreen.compose()` (lines 54-78), update hardcoded shortcut text:
- `F3` → `Ctrl+R`
- `F2` → `Ctrl+E`
- `F5` → `Ctrl+P`
- `F6` → `Ctrl+I`
- Add `Ctrl+Z` 撤销

- [ ] **Step 4: Update on_mount border titles**

In `on_mount()` (lines 583-586):

```python
# BEFORE:
self.query_one("#sidebar_pane").border_title = f"图片列表 ({Path.cwd().name}) [F6]"
self.query_one("#editor_section").border_title = "内容编辑 (F2)"
self.query_one("#preview_section").border_title = "分段预览 (F5)"

# AFTER:
self.query_one("#sidebar_pane").border_title = f"图片列表 ({Path.cwd().name}) [Ctrl+I]"
self.query_one("#editor_section").border_title = "内容编辑 (Ctrl+E)"
self.query_one("#preview_section").border_title = "分段预览 (Ctrl+P)"
```

- [ ] **Step 5: Run lint**

```bash
python -m ruff check snapshow/tui.py
```

- [ ] **Step 6: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: unify shortcuts to Ctrl+R/E/P/I, add undo, update HelpScreen and border titles"
```

---

### Task 10: Layer 4 — tui.py action_save fix + new UI controls

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: Add new Input widgets to compose()**

In `compose()` method, after the `#controls` Horizontal block, add a new Horizontal block:

```python
with Horizontal(id="controls_row2"):
    yield Label("FPS:", id="fps_label")
    yield Input(value="30", id="project_fps_input", width=6)
    yield Label("宽:", id="width_label")
    yield Input(value="1080", id="project_width_input", width=6)
    yield Label("高:", id="height_label")
    yield Input(value="1920", id="project_height_input", width=6)
    yield Label("语音:", id="voice_label")
    yield Input(value="zh-CN-XiaoxiaoNeural", id="default_voice_input", width=20)
```

- [ ] **Step 2: Add CSS for controls_row2**

In the CSS section, add after `#controls`:

```css
#controls_row2 {
    height: 3;
    background: $surface;
    border-top: solid $panel;
    layout: horizontal;
    padding: 0 1;
}

#controls_row2 > * {
    height: 100%;
    content-align: left middle;
    color: $text;
}

#fps_label, #width_label, #height_label, #voice_label {
    margin-right: 1;
    color: $text;
}

#project_fps_input, #project_width_input, #project_height_input, #default_voice_input {
    height: 1;
    background: $background;
    color: $text;
    border: none;
    padding: 0 1;
    margin-right: 2;
}
```

- [ ] **Step 3: Update load_initial_config() to populate new widgets**

In `load_initial_config()` (lines 617-655), after setting title and logo:

```python
# After line 635 (logo input):
fps = project.get("fps", 30)
width = project.get("width", 1080)
height = project.get("height", 1920)
self.query_one("#project_fps_input", Input).value = str(fps)
self.query_one("#project_width_input", Input).value = str(width)
self.query_one("#project_height_input", Input).value = str(height)

# Extract voice from first subtitle if available
subtitles = config.get("subtitles", [])
if subtitles and "voice" in subtitles[0]:
    voice = subtitles[0]["voice"].get("voice", "zh-CN-XiaoxiaoNeural")
    self.query_one("#default_voice_input", Input).value = voice
```

- [ ] **Step 4: Update action_save() to read from UI controls**

In `action_save()` (lines 793-844), replace hardcoded values:

```python
# BEFORE:
        config_dict = {
            "project": {
                "name": "tui_project",
                "fps": 30,
                "width": 1080,
                "height": 1920,
                ...
            },
            ...
        }
        ...
                config_dict["subtitles"].append({
                    ...
                    "voice": {"voice": "zh-CN-XiaoxiaoNeural"},
                })

# AFTER:
        # Read values from UI controls with error handling
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

        config_dict = {
            "project": {
                "name": "tui_project",
                "fps": fps,
                "width": width,
                "height": height,
                "output_dir": "./output",
                "title": title,
                "logo": logo,
            },
            "images": [],
            "subtitles": [],
        }
        ...
                config_dict["subtitles"].append({
                    ...
                    "voice": {"voice": voice},
                })
```

- [ ] **Step 5: Run lint**

```bash
python -m ruff check snapshow/tui.py
```

- [ ] **Step 6: Commit**

```bash
git add snapshow/tui.py
git commit -m "fix: action_save reads fps/width/height/voice from UI controls, add new input widgets"
```

---

### Task 11: Layer 4 — tui.py code cleanup + layout optimization

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: Delete duplicate #char_limit CSS**

Remove the second `#char_limit` definition (lines 549-556), keeping only the first one (lines 518-523).

- [ ] **Step 2: Fix ImageFileTree.filter_paths — remove redundant list comp + add mtime sort**

Replace the `filter_paths` method:

```python
# BEFORE:
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [
            p for paths in [paths]
            for p in paths
            if not p.name.startswith(".") and (
                p.is_dir() or p.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
        ]

# AFTER:
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        filtered = [
            p for p in paths
            if not p.name.startswith(".") and (
                p.is_dir() or p.suffix.lower() in {".jpg", ".jpeg", ".png"}
            )
        ]
        return sorted(filtered, key=lambda p: p.stat().st_mtime, reverse=True)
```

- [ ] **Step 3: Update refresh_preview() with timestamps**

Replace the `refresh_preview` method's ListItem creation:

```python
# BEFORE:
        for i, seg in enumerate(segments):
            display_text = seg
            est_duration = len(seg) * 0.25 + 0.5

            item = ListItem(
                Static(f"[b]{i + 1}.[/][segment-text] {display_text} [/] [segment-meta]({est_duration:.1f}s)[/]"),
                classes="segment-item",
            )
            self.preview_list.append(item)

# AFTER:
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

- [ ] **Step 4: Remove dead audio copy loop in run_generation_task**

In `run_generation_task()`, remove lines 901-906:
```python
# DELETE:
            final_audio_dir = work_dir / "audio"
            final_audio_dir.mkdir(parents=True, exist_ok=True)
            for sub_id, (path, duration) in audio_info.items():
                new_path = final_audio_dir / path.name
                shutil.copy2(path, new_path)
                audio_info[sub_id] = (new_path, duration)
```

- [ ] **Step 5: Use temp_work_dir in run_generation_task**

Wrap the generation logic:

```python
# BEFORE:
            audio_dir = Path(tempfile.mkdtemp()) / "audio"
            audio_info = generate_voices(config.subtitles, audio_dir)
            ...
            work_dir = Path(tempfile.mkdtemp()) / "snapshow_work"
            work_dir.mkdir(parents=True, exist_ok=True)
            ...
            output_path = generate_video(config, timeline, work_dir, base_dir)

# AFTER:
            from snapshow.utils import temp_work_dir

            with temp_work_dir() as audio_parent:
                audio_dir = audio_parent / "audio"
                audio_dir.mkdir()
                audio_info = generate_voices(config.subtitles, audio_dir)
                
                timeline = build_timeline(...)
                
                with temp_work_dir() as work_dir:
                    output_path = generate_video(config, timeline, work_dir, base_dir)
```

- [ ] **Step 6: Run lint**

```bash
python -m ruff check snapshow/tui.py
```

- [ ] **Step 7: Commit**

```bash
git add snapshow/tui.py
git commit -m "refactor: cleanup duplicate CSS, fix filter_paths, add timestamps, fix temp dirs in TUI"
```

---

### Task 12: Layer 5 — conventions doc + pyproject.toml

**Files:**
- Create: `docs/CONVENTIONS.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create CONVENTIONS.md**

```markdown
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
```

- [ ] **Step 2: Update pyproject.toml**

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```
Expected: All tests PASS

- [ ] **Step 4: Run full lint**

```bash
python -m ruff check snapshow/ tests/
```

- [ ] **Step 5: Commit**

```bash
git add docs/CONVENTIONS.md pyproject.toml
git commit -m "docs: add development conventions and pytest config"
```

---

### Task 13: Final verification

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 2: Run full lint**

```bash
python -m ruff check snapshow/ tests/
python -m ruff format --check snapshow/ tests/
```

- [ ] **Step 3: Verify TUI launches**

```bash
python -m snapshow ui --help
```

- [ ] **Step 4: Verify CLI commands work**

```bash
python -m snapshow --help
python -m snapshow voices --help
```

- [ ] **Step 5: Final commit if all pass**

```bash
git status
```
