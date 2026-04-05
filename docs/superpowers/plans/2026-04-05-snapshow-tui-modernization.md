# Snapshow TUI 现代化与架构升级计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过组件化重构、交互联动增强及配置补全，提升 snapshow TUI 的专业度与丝滑感。

**Architecture:** 
- **组件化**：提取 `Sidebar`、`ProjectEditor`、`PreviewPanel` 为独立 Widget。
- **消息总线**：利用 Textual 的消息传递机制处理组件间联动。
- **样式增强**：引入 `:hover` 与状态驱动的 CSS。

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/tui.py` | 核心重构：拆分组件、实现联动、补齐 UI 控件。 |

---

### Task 1: TUI 架构组件化重构 (架构减重)

- [ ] **Step 1: 提取独立 Widget 类**
    - 创建 `Sidebar(Vertical)`：包含 `ImageFileTree` 和预览按钮逻辑。
    - 创建 `EditorSection(Vertical)`：封装文本编辑与项目基础配置控件。
    - 创建 `PreviewSection(Vertical)`：独立的分段预览列表组件。

- [ ] **Step 2: 迁移逻辑与状态**
    - 将 `update_thumbnail` 和预览按钮逻辑移入 `Sidebar`。
    - 统一通过 `App` 层的 reactive 属性或自定义消息进行通信。

- [ ] **Step 3: 验证功能回归**
    - 确保原有快捷键、文案加载、视频生成功能依然正常。

---

### Task 2: 交互体验深度增强 (丝滑联动)

- [ ] **Step 1: 增加按钮视觉反馈**
    - 为 `#preview_btn` 增加 `:hover` 样式（改变背景色/光泽）。
    - 增加 `:active` 状态反馈。

- [ ] **Step 2: 实现编辑器与预览双向联动**
    - **正向**：在编辑器中移动光标，下方预览列表自动高亮对应的分段。
    - **反向**：点击下方预览分段，编辑器光标跳转至对应文本行。

- [ ] **Step 3: 优化按钮触发机制**
    - 弃用物理坐标探测，改为标准的 Widget 点击事件监听。

---

### Task 3: 配置补全与遗留优化 (最后拼图)

- [ ] **Step 1: 实装 `powered_by` 开关**
    - 在 `controls_row2` 增加一个 `Checkbox` (署名：Powered by snapshow)。
    - 同步更新 `action_save` 和 `load_initial_config` 逻辑。

- [ ] **Step 2: 补齐缺失配置字段**
    - 确保 `transition_duration` 等字段在 UI 中可见且可调。

- [ ] **Step 3: 最终 Review 与 Commit**

```bash
git add snapshow/tui.py
git commit -m "refactor: modernize TUI architecture and enhance user interaction"
```
