# Snapshow README 全面升级计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 全面更新 README.md，突出智能分屏 2.0、语音生成重试机制、配置结构扁平化等核心特性，提升项目专业感。

**Architecture:** 
- **结构重组**：按功能深度、安装、快速开始、配置详解进行重写。
- **卖点突出**：增加“智能分屏示例”和“语音高可用性”章节。

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `README.md` | 全面重写，增加新特性说明，更新配置表。 |

---

### Task 1: 核心功能与 README 内容重构

- [ ] **Step 1: 编写“核心特性”章节**
    - 增加 **智能分屏 2.0 (Smart Subtitle Splitter)**：标点驱动分屏、内容清洗（去标点）、词组保护 (jieba)、末尾重平衡。
    - 增加 **高可靠语音引擎 (High-Reliability Voice)**：8 次指数退避重试 (Exponential Backoff with Jitter)、实时 TUI 进度通知。

- [ ] **Step 2: 更新“快速开始”与快捷键说明**
    - 完善 TUI 操作指南。
    - 增加 `Ctrl+O` 用户级配置与扁平化项目配置的关联说明。

- [ ] **Step 3: 更新“配置详解”表格**
    - 反映最新的 `project` 键下扁平化的语音配置（voice, voice_rate, voice_volume, voice_pitch）。

- [ ] **Step 4: 增加示例对比部分**
    - 展示“标点优先 & 洁净输出”前后的字幕对比。

- [ ] **Step 5: 最终 Review 与 Commit**

```bash
git add README.md
git commit -m "docs: major README update to reflect smart splitting and voice retry features"
```
