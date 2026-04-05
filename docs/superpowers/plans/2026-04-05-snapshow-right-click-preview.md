# Snapshow 静默右键高清预览实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现右键点击图片列表项时调用系统看图软件，且不改变当前 TUI 选中的图片及文案。

**Architecture:** 
- **事件捕捉**：监听 `on_mouse_down` (或 `on_click`) 并判断 `event.button == 3`。
- **空间定位**：通过 `event.style.meta.get("node")` 获取被点击的 Tree 节点 ID。
- **状态保护**：通过直接操作 `tree.get_node(node_id)` 获取路径，避免触发全局 `highlighted` 事件。

**Tech Stack:** Python, Textual

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/tui.py` | 实现右键逻辑拦截、节点反查及静默弹窗。 |

---

### Task 1: 实现右键静默预览逻辑

- [ ] **Step 1: 修改 snapshow/tui.py 移除旧的双击追踪**

在 `__init__` 中删除 `self._last_click_time = 0`。

- [ ] **Step 2: 重写 on_click 或添加 on_mouse_down**

```python
    def on_mouse_down(self, event: events.MouseDown) -> None:
        """右键点击：静默调用系统看图预览"""
        if event.button == 3:  # 右键
            tree = self.query_one(ImageFileTree)
            # 通过鼠标位置对应的样式元数据找到 node id
            node_id = event.style.meta.get("node")
            if node_id is not None:
                try:
                    node = tree.get_node(node_id)
                    if node and node.data and hasattr(node.data, "path"):
                        path = Path(node.data.path)
                        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                            open_file_with_system_default(path)
                            # 阻止事件进一步传播，防止右键导致节点被选中（取决于 Textual 内部实现）
                            event.stop()
                except Exception:
                    pass
```

- [ ] **Step 3: 更新提示文案**

将 `sidebar_hint` 修改为：`"右键图片: 预览高清原图"`。

- [ ] **Step 4: 手动验证**

1. 启动 TUI: `./.venv/bin/python3 -m snapshow ui`
2. 选中图 A（看到图 A 文案）。
3. **右键**点击图 B。
4. **预期**：弹出图 B 的系统看图窗口，但 TUI 依然保持图 A 高亮，文案不变。

- [ ] **Step 5: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: implement non-intrusive right-click image preview"
```
