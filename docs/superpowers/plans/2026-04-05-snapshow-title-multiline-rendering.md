# Snapshow 标题片多行自动换行实施计划 (Revised)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现标题片内部文字根据 `max_chars` 智能换行，并在 FFmpeg 渲染中保持垂直/水平居中。

**Architecture:** 
- **预处理**：在 `timeline.py` 的 `build_timeline` 中，识别 `__title__` 段落，调用 `split_text_smart` 并在其第一个字幕项中注入带 `\n` 的多行文本。
- **渲染优化**：更新 `video.py`，确保标题渲染从 `segment.subtitles[0].text` 读取内容，并配置 `drawtext` 滤镜支持多行居中。

**Tech Stack:** Python, FFmpeg

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/timeline.py` | 在构建标题段落时，对标题文本执行语义换行处理。 |
| Modify | `snapshow/video.py` | 优化 FFmpeg drawtext 滤镜以支持多行居中，并切换数据源。 |
| Modify | `tests/test_timeline.py` | 验证标题段落的字幕文本中是否包含预期的换行符。 |

---

### Task 1: 标题文本换行预处理实现 (TDD)

- [ ] **Step 1: 在 tests/test_timeline.py 中编写换行测试**

```python
def test_title_multiline_wrapping():
    from snapshow.timeline import build_timeline
    from snapshow.config import ImageConfig, SubtitleConfig
    
    images = [ImageConfig(id="img1", path="img1.jpg", text="test")]
    subtitles = [SubtitleConfig(id="s1", text="test", image="img1")]
    audio_info = {"img1": (Path("img1.mp3"), 2.0), "__title__": (Path("title.mp3"), 2.0)}
    
    title = "这是一个非常非常长的标题文字测试"
    # 模拟 max_chars = 5，预期产生换行符
    timeline = build_timeline(images, subtitles, audio_info, title=title, max_chars=5)
    
    # 标题段落应该是第一个
    title_segment = timeline[0]
    assert title_segment.image_id == "__title__"
    assert "\n" in title_segment.subtitles[0].text
```

- [ ] **Step 2: 运行测试验证失败**

Run: `./.venv/bin/python3 -m pytest tests/test_timeline.py -v`

- [ ] **Step 3: 修改 snapshow/timeline.py 实现换行**

在 `build_timeline` 函数的标题处理块：
1. 调用 `title_segments = split_text_smart(title, max_chars)`。
2. 拼接：`multiline_text = "\n".join([s[1] for s in title_segments])`。
3. 将 `multiline_text` 存入 `SubtitleConfig(id="__title_sub__", text=multiline_text, ...)`。

- [ ] **Step 4: 运行测试验证通过**

Run: `./.venv/bin/python3 -m pytest tests/test_timeline.py -v`

---

### Task 2: 优化 FFmpeg 标题渲染 - snapshow/video.py

- [ ] **Step 1: 修改 snapshow/video.py 中的 drawtext 滤镜**

在渲染 `image_id == "__title__"` 的逻辑处：
1. 核心变更：将文本来源从 `config.title` 改为 `seg.subtitles[0].text`。
2. 滤镜参数：确保 `x=(w-text_w)/2:y=(h-text_h)/2`。
3. 增加 `text_align=center` 支持（如果环境 FFmpeg 版本支持）。

- [ ] **Step 2: 运行全量测试确保无回归**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 3: Final Commit**

```bash
git add .
git commit -m "feat: implement semantic multiline wrapping for title slide"
```
