# Snapshow 分辨率感知型自动分屏实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 TUI 中手动切换分辨率时，根据横竖屏自动推荐并更新字数限制（横 15/竖 10）。

**Architecture:** 
- **事件监听**：在 `SubtitleTUI` 中添加 `on_select_changed`。
- **状态同步**：更新 `self.max_chars` 及其关联的 Input 控件，并强制触发预览刷新。

**Tech Stack:** Python, Textual

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/tui.py` | 实现分辨率解析、建议逻辑及 UI 同步。 |

---

### Task 1: 实现分辨率切换监听与自动建议

- [ ] **Step 1: 在 snapshow/tui.py 中添加 on_select_changed**

```python
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "project_resolution_select" and event.value:
            try:
                width, height = map(int, str(event.value).split("x"))
                # 如果用户切换分辨率，且此时不是在 load_initial_config 阶段
                # (load_initial_config 不会触发 Select.Changed 事件，因为它是直接赋 .value)
                if width > height:
                    # 横屏建议 15
                    self.max_chars = 15
                    self.notify("切换为横屏，每屏字数自动调整为 15")
                else:
                    # 竖屏建议 10
                    self.max_chars = 10
                    self.notify("切换为竖屏，每屏字数自动调整为 10")
                
                # 同步更新 UI
                char_limit_input = self.query_one("#char_limit", Input)
                char_limit_input.value = str(self.max_chars)
                self.refresh_preview()
            except Exception:
                pass
```

- [ ] **Step 2: 验证手动切换效果**

1. 启动 TUI: `./.venv/bin/python3 -m snapshow ui`
2. 选择一个 1080x1920 (竖屏) 的默认项目。
3. 在分辨率下拉框手动选择 `1920x1080`。
4. **预期**：右上角弹出通知，`每屏字数` 输入框自动变为 `15`，预览列表重新渲染。

- [ ] **Step 3: 验证加载配置不被覆盖**

1. 准备一个 `project_tui.yaml`，其中 `resolution: 1920x1080`, `max_chars: 10`。
2. 启动 TUI。
3. **预期**：加载后分辨率为 `1920x1080`，但 `每屏字数` 仍保持为 `10`（因为 `load_initial_config` 直接设置 `.value` 不会触发 `Select.Changed`）。

- [ ] **Step 4: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: auto-adjust max_chars based on orientation in TUI"
```
