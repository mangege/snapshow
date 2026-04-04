# Snapshow 语音生成重试退避实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为语音生成引入 8 次带 Jitter 的指数退避重试，并实装 TUI 进度通知。

**Architecture:** 
1. `voice.py`: 在 `generate_voice_async` 中封装重试逻辑，通过可选的 `on_retry` 回调暴露进度。
2. `tui.py`: 利用 `call_from_thread` 确保 TUI 能在生成线程中安全地弹出重试通知。

**Tech Stack:** Python, asyncio, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/voice.py` | 实现 `MAX_RETRIES` 指数退避和 `on_retry` 接口。 |
| Modify | `snapshow/tui.py` | 接入重试回调并实现 UI 通知逻辑。 |
| Modify | `tests/test_voice.py` | 验证重试序列、Jitter 及回调触发。 |

---

### Task 1: 核心重试逻辑实现 - snapshow/voice.py

**Files:**
- Modify: `snapshow/voice.py`
- Modify: `tests/test_voice.py`

- [ ] **Step 1: 在 tests/test_voice.py 编写重试测试用例**

```python
@pytest.mark.asyncio
async def test_generate_voice_retry_logic():
    from snapshow.voice import generate_voice_async
    import asyncio
    
    # Mock Communicate 抛出异常
    with patch("snapshow.voice.edge_tts.Communicate") as mock_comm:
        mock_comm.side_effect = Exception("Network Error")
        
        retries = []
        def on_retry(attempt, error, wait):
            retries.append((attempt, wait))
            
        # 缩短 sleep 时间以便测试快速运行
        with patch("snapshow.voice.asyncio.sleep", return_value=None):
            with pytest.raises(RuntimeError, match="语音生成最终失败"):
                await generate_voice_async("test", "out.mp3", on_retry=on_retry)
        
        assert len(retries) == 7 # 第1次执行，之后重试7次 (总8次)
        assert retries[0][0] == 1 # 第一次重试编号
```

- [ ] **Step 2: 运行测试验证失败**

Run: `./.venv/bin/python3 -m pytest tests/test_voice.py -v`
Expected: FAIL (Unexpected keyword argument 'on_retry')

- [ ] **Step 3: 修改 voice.py 实现重试循环**

在 `snapshow/voice.py` 中：
1. 定义 `MAX_RETRIES = 8`。
2. 重构 `generate_voice_async`，添加 `on_retry` 参数。
3. 在 `while attempt < MAX_RETRIES` 循环中尝试生成。
4. 失败时计算 `(2 ** attempt) + random.random()`。
5. 更新 `generate_voices` 同步支持 `on_retry` 并透传。

- [ ] **Step 4: 运行测试验证通过**

Run: `./.venv/bin/python3 -m pytest tests/test_voice.py -v`

- [ ] **Step 5: Commit**

```bash
git add snapshow/voice.py tests/test_voice.py
git commit -m "feat: implement exponential backoff retry in voice generation"
```

---

### Task 2: TUI 集成与进度反馈

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: 在 run_generation_task 中定义并传入重试回调**

```python
            def on_voice_retry(attempt: int, error: str, wait: float):
                self.app.call_from_thread(
                    self.notify, 
                    f"语音生成重试 ({attempt}/{MAX_RETRIES-1}): {error[:30]}... 等待 {wait:.1f}s",
                    severity="warning"
                )

            # 调用 generate_voices 时传入
            audio_info = generate_voices(..., on_retry=on_voice_retry)
```

- [ ] **Step 2: 运行并验证 TUI 交互**

断开网络或修改 `voice.py` 制造临时失败，观察 TUI 是否弹出重试通知。

- [ ] **Step 3: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: show voice retry notifications in TUI"
```

---

### Task 3: 最终集成测试

- [ ] **Step 1: 运行全量测试**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 2: 检查 CLI 模式兼容性**

Run: `python -m snapshow --help` (确保不因参数变更报错)

- [ ] **Step 3: Final Commit**

```bash
git commit --allow-empty -m "chore: complete voice retry logic with TUI feedback"
```
