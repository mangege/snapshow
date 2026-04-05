# Snapshow 分辨率感知型自动分屏设计文档

> 日期：2026-04-05
> 状态：待实现
> 目标：在 TUI 中手动切换屏幕分辨率时，根据横屏或竖屏的特性，自动调整 `max_chars`（每屏字数限制），提升阅读节奏的视觉适配性。

## 1. 核心逻辑 (Logic)

### 1.1 分辨率解析 (Resolution Parsing)
- **触发点**：`Select.Changed` 事件，监听 ID 为 `project_resolution_select` 的组件。
- **宽度与高度提取**：解析格式如 `1920x1080` 的字符串。
- **横/竖屏判定**：
    - **横屏 (Landscape)**: `width > height`
    - **竖屏 (Portrait)**: `width <= height`

### 1.2 智能建议策略 (Smart Recommendations)
- **横屏切换**：
    - `max_chars` 自动设置为 **20**。
    - **用户通知**：`"切换为横屏，每屏字数自动调整为 20"` (severity="info")。
- **竖屏切换**：
    - `max_chars` 自动设置为 **10**。
    - **用户通知**：`"切换为竖屏，每屏字数自动调整为 10"` (severity="info")。

## 2. 交互细节 (UI Consistency)

### 2.1 状态同步 (State Synchronization)
- 自动更新 `Input#char_limit` 的 `.value`。
- **预览刷新**：立即调用 `self.refresh_preview()`，实时展现分段变化。

### 2.2 优先权原则 (Priority)
1. **加载已有配置 (Load Config)**：**禁止** 自动调整。`max_chars` 严格遵循配置文件（YAML）中的原始设置。
2. **用户手动微调**：在自动建议后，如果用户再次手动修改 `Input#char_limit`，系统需保留用户最新输入的数值。

## 3. 实现说明 (Implementation)

- **文件**：`snapshow/tui.py`
- **新增方法**：`on_select_changed(self, event: Select.Changed) -> None`
- **逻辑分支**：通过 `event.select.id == "project_resolution_select"` 进行隔离判断。

---

**预期效果**：用户切换屏幕方向时，预览列表同步响应并自动适配最佳字数限制，极大提升了内容策划的交互效率。
