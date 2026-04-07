# Snapshow 全系统日志链路加固实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 确保所有逻辑分支（含外部进程、异步任务、TUI 生命周期）产生的异常均能携带完整堆栈信息记入 `snapshow.log`。

**Architecture:** 
- **捕获前移**：在所有 `try-except` 块中补齐 `logger.error(..., exc_info=True)`。
- **外部进程加固**：在 `_run_ffmpeg` 和 `_detect_gpu_encoder` 中强制捕获并记录 `stderr`。
- **异步安全**：在 Textual `@work` 任务中增加顶层异常捕获。

**Tech Stack:** Python, Logging, FFmpeg

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/video.py` | 加固外部进程调用日志。 |
| Modify | `snapshow/tui.py` | 加固 TUI 事件与后台 Worker 日志。 |
| Modify | `snapshow/utils.py` | 增加工具函数调用的异常记录。 |

---

### Task 1: 加固外部进程调用日志 - snapshow/video.py

- [ ] **Step 1: 完善 _detect_gpu_encoder 日志**

```python
    except Exception as e:
        logger.warning(f"GPU 检测过程中出现非预期错误: {e}")
        return None
```

- [ ] **Step 2: 确保 _run_ffmpeg 始终记录失败上下文**

检查 `_run_ffmpeg` 是否在抛出异常前已记录命令详情和 `stderr`。

- [ ] **Step 3: Commit**

```bash
git add snapshow/video.py
git commit -m "fix: harden external process logging in video.py"
```

---

### Task 2: 加固 TUI 生命周期与异步 Worker - snapshow/tui.py

- [ ] **Step 1: 加固 load_initial_config 与 save 逻辑**

为 `load_initial_config`, `action_save`, `handle_load_decision` 等涉及文件 IO 的 `try-except` 块补齐：
```python
logger.error(f"操作失败: {str(e)}", exc_info=True)
```

- [ ] **Step 2: 加固异步任务 (Workers)**

为 `warm_up_jieba` 和 `Sidebar.update_thumbnail` (及其关联的 `on_tree_node_highlighted`) 增加显式异常记录。

- [ ] **Step 3: 优化 UILogHandler**

确保它在捕捉日志的同时，不会意外吞掉 `ERROR` 级别的信号向上层 Handler 传播。

- [ ] **Step 4: Commit**

```bash
git add snapshow/tui.py
git commit -m "fix: harden TUI events and async worker logging"
```

---

### Task 3: 全系统集成验证

- [ ] **Step 1: 运行全量测试**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 2: 制造故障并检查 snapshow.log**

故意损坏 `project_tui.yaml` 或移动 FFmpeg 路径，验证 `snapshow.log` 是否包含详细 Traceback。

- [ ] **Step 3: Final Commit**

```bash
git commit --allow-empty -m "chore: complete full system log hardening"
```
