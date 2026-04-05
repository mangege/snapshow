# Snapshow TUI 内置图片预览实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 TUI 左侧边栏下方实现基于 ANSI 的实时图片缩略图预览。

**Architecture:** 
- **渲染引擎**：在 `utils.py` 中利用 Pillow 实现像素到 ANSI 的高效转换。
- **UI 集成**：在 `tui.py` 中重塑侧边栏布局，添加 `thumbnail_preview` 控件。
- **性能优化**：使用 Textual `@work` 进行异步渲染并配合 `lru_cache`。

**Tech Stack:** Python, Pillow, Textual, rich

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/utils.py` | 实现 `render_image_to_ansi` 渲染器。 |
| Modify | `snapshow/tui.py` | 实现 UI 布局重构及异步加载逻辑。 |
| Create | `tests/test_image_render.py` | 验证 ANSI 渲染逻辑的准确性。 |

---

### Task 1: 实现 ANSI 图片渲染器 - snapshow/utils.py

**Files:**
- Modify: `snapshow/utils.py`
- Create: `tests/test_image_render.py`

- [ ] **Step 1: 编写渲染器测试用例**

```python
def test_render_image_to_ansi_exists():
    from snapshow.utils import render_image_to_ansi
    from PIL import Image
    import io

    # 创建一个小的红色图片
    img = Image.new('RGB', (10, 10), color='red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    
    # 只要不报错且返回字符串即可
    ansi_str = render_image_to_ansi(img, width=5)
    assert isinstance(ansi_str, str)
    assert len(ansi_str) > 0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `./.venv/bin/python3 -m pytest tests/test_image_render.py -v`

- [ ] **Step 3: 实现 render_image_to_ansi**

在 `snapshow/utils.py` 中利用 `rich.console.Console` 和 `rich.image.Image` (如果可用) 或手动实现像素转换。建议方案：
1. 使用 Pillow 缩放图片。
2. 遍历像素，利用 ANSI 256 色转义码拼接字符串。
3. 添加 `@lru_cache(maxsize=32)`。

- [ ] **Step 4: 运行测试验证通过**

Run: `./.venv/bin/python3 -m pytest tests/test_image_render.py -v`

---

### Task 2: 重构 TUI 布局并集成预览 - snapshow/tui.py

- [ ] **Step 1: 修改 CSS 布局**

更新 `SubtitleTUI.CSS`：
1. `#sidebar_pane` 设为 `Vertical` 布局。
2. 为 `#thumbnail_preview` 设置边框、高度 (约 30%) 和居中显示。

- [ ] **Step 2: 修改 compose 并注入控件**

1. 在 `compose` 方法的 `sidebar_pane` 中 `yield Static(id="thumbnail_preview")`。
2. 在 `on_mount` 中为该控件设置初始占位符（如“未选中”）。

- [ ] **Step 3: 实现异步渲染 Worker**

在 `SubtitleTUI` 中添加：
```python
    @work(exclusive=True)
    async def update_thumbnail(self, path: Path):
        self.query_one("#thumbnail_preview").update("渲染中...")
        # 调用 utils 中的渲染器
        ansi_str = await asyncio.to_thread(render_image_to_ansi_from_path, path, width=30)
        self.query_one("#thumbnail_preview").update(ansi_str)
```

- [ ] **Step 4: 挂接事件信号**

在 `on_directory_tree_file_selected` 中调用 `self.update_thumbnail(event.path)`。

- [ ] **Step 5: 启动 TUI 验证效果**

Run: `./.venv/bin/python3 -m snapshow ui`
1. 点击图片，观察左下方是否出现 ANSI 缩略图。
2. 确认渲染期间 UI 不卡顿。

---

### Task 3: 最终集成与 Commit

- [ ] **Step 1: 运行全量测试**
- [ ] **Step 2: Final Commit**

```bash
git add snapshow/utils.py snapshow/tui.py tests/test_image_render.py
git commit -m "feat: implement ANSI image preview in TUI sidebar"
```
