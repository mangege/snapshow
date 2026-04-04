# Snapshow 标点优先 & 洁净分屏实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现标点符号触发强制分屏，并在输出中移除除数值/符号外的所有常规标点。

**Architecture:** 
1. **预处理分屏**：使用正则匹配“非数字环绕”的标点符号作为切分点。
2. **内容清洗**：遍历切分后的段落，剥离非必要标点。
3. **二次切分**：对清洗后仍超长的段落执行 Jieba 分段。

**Tech Stack:** Python, re, jieba

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `snapshow/utils.py` | 实现标点识别、内容清洗及 `split_text_smart` 逻辑重组。 |
| Modify | `tests/test_utils.py` | 验证去标点效果、小数点保留及分屏优先级。 |

---

### Task 1: 核心清洗与切分算法实现 - snapshow/utils.py

**Files:**
- Modify: `snapshow/utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: 在 tests/test_utils.py 编写洁净分屏测试用例**

```python
def test_split_text_smart_punctuation_priority():
    from snapshow.utils import split_text_smart
    text = "好的，没问题！我这就去。"
    # 预期：标点强制分屏，且输出无标点
    segments = split_text_smart(text, max_chars=10)
    assert segments == ["好的", "没问题", "我这就去"]

def test_split_text_smart_keep_numeric_symbols():
    from snapshow.utils import split_text_smart
    text = "当前进度是 98.5%，增长了 +5 左右。"
    segments = split_text_smart(text, max_chars=20)
    # 预期：保留小数点、百分号、正号
    assert "98.5%" in segments[0]
    assert "+5" in segments[1]
    assert "。" not in segments[1]
```

- [ ] **Step 2: 运行测试验证失败**

Run: `./.venv/bin/python3 -m pytest tests/test_utils.py -v`

- [ ] **Step 3: 重写 split_text_smart 算法**

在 `snapshow/utils.py` 中更新逻辑：
1. 实现 `_is_smart_split_point(char, prev_char, next_char)` 辅助判断或直接使用复杂的 Lookahead 正则。
2. 切分逻辑：
   - 匹配标点 `[，。！？；、,!?;:\"')}\]]`。
   - 排除：被数字包围的 `.` 和 `,`。
3. 清洗函数：
   - 移除常规标点，保留 `[0-9.%+-]` 和 Emoji。
4. 整合现有 Jieba 逻辑处理超长片段。

- [ ] **Step 4: 运行测试验证通过**

Run: `./.venv/bin/python3 -m pytest tests/test_utils.py -v`

- [ ] **Step 5: Commit**

```bash
git add snapshow/utils.py tests/test_utils.py
git commit -m "feat: implementation of punctuation-first clean splitter"
```

---

### Task 2: 最终集成与冒烟测试

- [ ] **Step 1: 运行全量测试套件**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 2: 在 TUI 中手动验证视觉效果**

启动：`./.venv/bin/python3 -m snapshow ui`
输入：`专为普通投资者打造的，宽指基金筛选网站，终于做好啦！`
观察：是否呈现为三段，且末尾无“！”等符号。

- [ ] **Step 3: Final Commit**

```bash
git commit --allow-empty -m "chore: complete punctuation-driven subtitle splitting"
```
