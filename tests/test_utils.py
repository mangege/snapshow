"""测试跨平台工具模块"""

from snapshow.utils import find_ffmpeg, find_ffprobe, find_zh_font, temp_work_dir


class TestTempWorkDir:
    def test_creates_and_cleans_up(self):
        dir_path = None
        with temp_work_dir() as tmp:
            dir_path = tmp
            assert tmp.is_dir()
            (tmp / "test.txt").write_text("hello")
            assert (tmp / "test.txt").read_text() == "hello"
        assert not dir_path.exists()

    def test_cleans_up_on_exception(self):
        dir_path = None
        try:
            with temp_work_dir() as tmp:
                dir_path = tmp
                raise ValueError("boom")
        except ValueError:
            pass
        assert not dir_path.exists()

    def test_custom_prefix(self):
        with temp_work_dir(prefix="mytest") as tmp:
            assert "mytest" in tmp.name


class TestFindFfmpeg:
    def test_returns_string(self):
        result = find_ffmpeg()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_searches_linux_paths(self, monkeypatch):
        """On Linux, should search common paths"""
        monkeypatch.setattr("snapshow.utils.platform.system", lambda: "Linux")
        result = find_ffmpeg()
        assert isinstance(result, str)


class TestFindFfprobe:
    def test_returns_string(self):
        result = find_ffprobe()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_searches_linux_paths(self, monkeypatch):
        """On Linux, should search common paths"""
        monkeypatch.setattr("snapshow.utils.platform.system", lambda: "Linux")
        result = find_ffprobe()
        assert isinstance(result, str)


class TestFindZhFont:
    def test_returns_string_or_none(self, monkeypatch):
        """Should return a string (font name) or None"""
        monkeypatch.setattr("snapshow.utils.platform.system", lambda: "Linux")
        result = find_zh_font()
        assert result is None or isinstance(result, str)


class TestSplitTextSmart:
    def test_split_text_smart_punctuation_priority(self):
        """验证标点强制分屏且输出不含常规标点"""
        from snapshow.utils import split_text_smart
        text = "好的，没问题！我这就去。"
        segments = split_text_smart(text, max_chars=10)
        # 即使字数很少，标点也强制分段
        assert segments == ["好的", "没问题", "我这就去"]

    def test_split_text_smart_keep_numeric_symbols(self):
        """验证保留数值相关的符号和小数点"""
        from snapshow.utils import split_text_smart
        text = "当前进度是 98.5%，增长了 +5 左右。"
        segments = split_text_smart(text, max_chars=20)
        # 标点 "." 作为小数点应保留，"。" 作为句号应移除
        assert "98.5%" in segments[0]
        assert "+5" in segments[1]
        assert "。" not in segments[1]
        assert "." not in segments[1] # 句尾无点

    def test_split_text_smart_emoji_preservation(self):
        """验证表情符号被保留"""
        from snapshow.utils import split_text_smart
        text = "太棒了 😄！干得漂亮。"
        segments = split_text_smart(text, max_chars=10)
        assert "😄" in segments[0]
        assert "太棒了" in segments[0]
        assert "！" not in segments[0]

    def test_split_text_smart_balance(self):
        """验证在去标点后的长句依然执行智能平衡"""
        from snapshow.utils import split_text_smart
        text = "我们正在研究人工智能实验室的先进技术" # 18字
        max_chars = 10
        segments = split_text_smart(text, max_chars)
        assert len(segments) == 2
        assert all(len(s) <= max_chars for s in segments)
        assert abs(len(segments[0]) - len(segments[1])) <= 4

    def test_split_text_smart_long_word_fallback(self):
        """验证超长词组的保护与被迫切分"""
        from snapshow.utils import split_text_smart
        text = "人工智能"
        # 4字词组在3字限制下
        segments = split_text_smart(text, max_chars=3)
        assert segments == ["人工智能"] # 允许小幅超限保护词组
