# Snapshow 语音生成指数退避重试设计文档

> 日期：2026-04-04
> 状态：待实现
> 目标：通过带随机扰动的指数退避重试机制，增强 edge-tts 语音生成的稳定性，并实时向 UI 反馈重试进度。

## 1. 核心逻辑 (Backoff Algorithm)

### 1.1 `generate_voice_async` 增强
- **重试循环**：最大尝试 8 次。
- **异常捕获**：捕获所有 `Exception`（重点是网络超时与 edge-tts 连接异常）。
- **等待时间**：采用 `(2 ** attempt) + random.random()` 公式计算（Jitter）。
- **回调接口**：新增可选参数 `on_retry: Callable[[int, str, float], None]`，用于向外传递重试信息（尝试次数、失败原因、等待秒数）。

### 1.2 资源管理
- 每次尝试开始前，必须执行 `if output_path.exists(): output_path.unlink()`，确保音频流写入全新的文件。

## 2. UI 交互 (UX & Feedback)

### 2.1 实时通知
- 在 `SubtitleTUI.run_generation_task` 中，为 `generate_voices` 提供回调函数。
- 回调触发时，利用 `self.app.call_from_thread(self.notify, ...)` 在 TUI 主界面弹出提示，例如：“语音生成失败，正在进行第 3 次重试 (等待 4.2s)...”。

### 2.2 日志展示
- 重试详情将同步通过 `logger.warning` 输出到 `GenerationLogScreen`，确保用户可以查看失败的详细错误栈。

## 3. 实施步骤 (Implementation)

1. **接口变更**：更新 `generate_voice_async` 和 `generate_voices` 的签名，支持 `on_retry` 回调。
2. **重试环路**：在 `generate_voice_async` 中实现 `for attempt in range(8)` 逻辑。
3. **TUI 接入**：在 `tui.py` 的生成线程中定义并传入 UI 通知回调。
4. **验证**：编写测试用例，通过 Mock 制造连续失败，验证退避时间序列和回调触发。

## 4. 交付物 (Deliverables)

- 具备指数退避能力的 `snapshow/voice.py`。
- 能够显示重试进度的 `snapshow/tui.py`。
- 针对重试逻辑的单元测试。
