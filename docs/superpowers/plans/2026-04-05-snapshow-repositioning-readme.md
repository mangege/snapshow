# Snapshow 品牌定位重构实施计划 (README Update)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面更新 README.md，将其从“自动化生成工具”重塑为“专业的图文成片交付引擎”，突出极客化的高效交付。

**Architecture:** 
- **叙事重组**：从“工具 -> 功能”模式转变为“愿景 -> 工作流 -> 核心交付特性”模式。
- **术语升级**：将分屏功能描述为“视觉节奏控制”，配音重试描述为“工业级保障”。

**Tech Stack:** Markdown

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `README.md` | 重写所有核心章节，反映新的品牌定位和技术特性。 |

---

### Task 1: 愿景与工作流重写

- [ ] **Step 1: 重写 Header 和 Vision 章节**
    - 标题改为：`snapshow —— 专业的图文成片交付引擎`。
    - 强调定位：专为追求效率与极致观感的创作者打造，高效转化预处理好的图文素材。
    - 明确“非 AI 生成器”属性：人工编辑为主，AI 素材为辅。

- [ ] **Step 2: 增加“推荐工作流 (Workflow)”章节**
    - **外部创作**：AI 生成图文或人工整理素材。
    - **逻辑对齐**：使用 TUI 进行视觉节奏校对与智能分屏。
    - **合成交付**：FFmpeg 高速合成与 8 次配音重试保障。

- [ ] **Step 3: 提交初步重构**

```bash
git add README.md
git commit -m "docs: revamp README vision and workflow as a delivery engine"
```

---

### Task 2: 核心交付特性与技术参考更新

- [ ] **Step 1: 更新特性列表 (Core Features)**
    - **视觉节奏控制 (Splitter 2.0)**：标点驱动、极致洁净字幕（去标点）、jieba 语义平衡。
    - **高可用配音保障**：8 次指数退避重试，无惧网络波动。
    - **工业级极客效率**：基于原生 FFmpeg，自动硬件加速调度。

- [ ] **Step 2: 更新配置详解 (Config Reference)**
    - 反映扁平化的 `ProjectConfig` (voice 设置直接在 project 下)。
    - 增加 `max_chars` 字段及其对视觉节奏的影响说明。

- [ ] **Step 3: 更新快捷键与安装说明**
    - 确保所有命令（如 `python -m snapshow ui`）准确。
    - 统一使用极简专业的话术。

- [ ] **Step 4: 最终核对并 Commit**

```bash
git add README.md
git commit -m "docs: update feature details and config table for new positioning"
```
