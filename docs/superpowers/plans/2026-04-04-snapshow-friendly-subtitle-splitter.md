# Snapshow 友好型字幕分屏实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 引入 `jieba` 分词和智能平衡算法，将字幕分段逻辑迁移至 `utils.py`，提升视觉均衡性和语义完整性。

**Architecture:** 
1. 迁移逻辑：在 `utils.py` 中实现独立的分词与平衡算法。
2. 算法分层：先按标点切分，再对长句应用 `jieba` 贪婪合并，最后进行末尾重平衡。
3. 性能优化：TUI 启动时在 `on_mount` 异步初始化 `jieba`。

**Tech Stack:** Python, jieba, pytest

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `requirements.txt` | 添加 `jieba` 依赖。 |
| Modify | `snapshow/utils.py` | 实现 `split_text_smart` 及相关辅助函数。 |
| Modify | `snapshow/tui.py` | 调用 `utils.split_text_smart`；添加 `jieba` 预热逻辑。 |
| Modify | `tests/test_utils.py` | 验证分屏算法的均衡性和语义保护。 |

---

### Task 1: 环境准备

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加 jieba 到 requirements.txt**

```text
jieba>=0.42.1
```

- [ ] **Step 2: 安装依赖**

Run: `./.venv/bin/pip install jieba`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add jieba for smarter subtitle splitting"
```

---

### Task 2: 核心算法实现 - snapshow/utils.py

**Files:**
- Modify: `snapshow/utils.py`
- Modify: `tests/test_utils.py`

- [ ] **Step 1: 在 tests/test_utils.py 编写分段测试用例**

```python
def test_split_text_smart_balance():
    from snapshow.utils import split_text_smart
    text = "我们正在研究人工智能实验室的先进技术" # 18字
    max_chars = 10
    # 预期：不应该是 [10, 8]，而应该是更均衡的 [9, 9] 或类似
    segments = split_text_smart(text, max_chars)
    assert len(segments) == 2
    assert all(len(s) <= max_chars for s in segments)
    assert abs(len(segments[0]) - len(segments[1])) <= 2

def test_split_text_smart_word_protection():
    from snapshow.utils import split_text_smart
    text = "人工智能"
    # 预期：即使限制为2，也不应切断词组（除非词组本身超限）
    segments = split_text_smart(text, max_chars=3)
    assert segments == ["人工智能"] # 超限被迫保留或按字符切
```

- [ ] **Step 2: 运行测试验证失败**

Run: `./.venv/bin/python3 -m pytest tests/test_utils.py -v`
Expected: ImportError (split_text_smart not found)

- [ ] **Step 3: 实现 split_text_smart 算法**

在 `snapshow/utils.py` 中添加：
```python
import re
import jieba

def split_text_smart(text: str, max_chars: int) -> list[str]:
    """
    智能分段算法：
    1. 按强标点分割
    2. 对长片段使用 jieba 分词
    3. 贪婪合并并保护词组边界
    4. 末尾重平衡（Redistribution）
    """
    if not text:
        return []
    
    # 1. 强标点切分
    parts = re.split(r"([\n。！？；])", text)
    processed_parts = []
    for i in range(0, len(parts)-1, 2):
        processed_parts.append(parts[i] + parts[i+1])
    if len(parts) % 2 == 1:
        processed_parts.append(parts[-1])
    
    final_segments = []
    for part in processed_parts:
        part = part.strip()
        if not part: continue
        
        if len(part) <= max_chars:
            final_segments.append(part)
            continue
            
        # 2. Jieba 分词贪婪合并
        words = list(jieba.cut(part))
        sub_segments = []
        current_seg = ""
        
        for word in words:
            # 标点避头处理：如果是标点且 current_seg 不为空，强行贴附
            if word in "，、, . : ; \" ' ) } ]" and current_seg:
                if len(current_seg) + len(word) <= max_chars:
                    current_seg += word
                    continue
            
            if len(current_seg) + len(word) <= max_chars:
                current_seg += word
            else:
                if current_seg:
                    sub_segments.append(current_seg)
                # 处理超长单调词
                while len(word) > max_chars:
                    sub_segments.append(word[:max_chars])
                    word = word[max_chars:]
                current_seg = word
        
        if current_seg:
            sub_segments.append(current_seg)
            
        # 3. 智能平衡 (针对最后两段)
        if len(sub_segments) >= 2:
            last = sub_segments[-1]
            prev = sub_segments[-2]
            # 如果最后一段太短（小于1/3），尝试从前一段匀词
            if len(last) < max_chars * 0.4 and (len(prev) + len(last)) <= max_chars * 1.5:
                # 重新对这两段进行平分尝试 (以词为单位)
                combined_words = list(jieba.cut(prev + last))
                total_len = len(prev) + len(last)
                target_len = total_len / 2
                
                new_prev = ""
                idx = 0
                for w in combined_words:
                    if len(new_prev) + len(w) <= target_len or not new_prev:
                        new_prev += w
                        idx += 1
                    else:
                        break
                new_last = "".join(combined_words[idx:])
                if new_last and len(new_prev) <= max_chars and len(new_last) <= max_chars:
                    sub_segments[-2] = new_prev
                    sub_segments[-1] = new_last
                    
        final_segments.extend(sub_segments)
        
    return final_segments
```

- [ ] **Step 4: 运行测试验证通过**

Run: `./.venv/bin/python3 -m pytest tests/test_utils.py -v`

- [ ] **Step 5: Commit**

```bash
git add snapshow/utils.py tests/test_utils.py
git commit -m "feat: implement smart subtitle splitting algorithm with jieba and balance logic"
```

---

### Task 3: TUI 集成与优化

**Files:**
- Modify: `snapshow/tui.py`

- [ ] **Step 1: 替换 tui.py 中的 split_text**

修改 `snapshow/tui.py`，导入 `split_text_smart` 并替换旧方法：
```python
from .utils import split_text_smart

# 在 SubtitleTUI 类中
def split_text(self, text: str, max_len: int) -> list[str]:
    return split_text_smart(text, max_len)
```

- [ ] **Step 2: 添加 Jieba 预热逻辑**

在 `on_mount` 中添加：
```python
    @work(thread=True)
    def warm_up_jieba(self):
        import jieba
        jieba.initialize()
        self.app.call_from_thread(self.notify, "分词引擎初始化完成", severity="information")

    def on_mount(self) -> None:
        # ... 原有代码 ...
        self.warm_up_jieba()
```

- [ ] **Step 3: 运行并手动验证 TUI**

Run: `./.venv/bin/python3 -m snapshow ui`
验证：输入长句，观察分屏是否比以前更均衡。

- [ ] **Step 4: Commit**

```bash
git add snapshow/tui.py
git commit -m "feat: integrate smart splitter into TUI and add jieba warm-up"
```

---

### Task 5: 最终集成验证

- [ ] **Step 1: 运行全量测试**

Run: `./.venv/bin/python3 -m pytest tests/ -v`

- [ ] **Step 2: 验证 CLI 模式是否受影响**

Run: `./.venv/bin/python3 -m snapshow voices --help`

- [ ] **Step 3: Final Commit**

```bash
git commit --allow-empty -m "chore: complete friendly subtitle splitter implementation"
```
