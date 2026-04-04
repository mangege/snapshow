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
        # Should return either a found path or 'ffmpeg' fallback
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
    def test_split_text_smart_basic(self):
        from snapshow.utils import split_text_smart
        text = "这是一个简单的测试句子。"
        segments = split_text_smart(text, max_chars=10)
        assert len(segments) == 2
        assert segments[0] == "这是一个简单的测试"
        assert segments[1] == "句子。"

    def test_split_text_smart_balance(self):
        """验证智能平衡：10+2 应调整为更均衡的 6+6 或类似"""
        from snapshow.utils import split_text_smart
        text = "我们正在研究人工智能实验室的先进技术"  # 18字
        max_chars = 10
        segments = split_text_smart(text, max_chars)
        # 如果不平衡可能是 [10, 8]，平衡后可能保持 [9, 9] 或 [10, 8] 取决于分词
        assert len(segments) == 2
        assert all(len(s) <= max_chars for s in segments)
        # 验证两段长度差异不应过大
        assert abs(len(segments[0]) - len(segments[1])) <= 4

    def test_split_text_smart_word_protection(self):
        """验证词组保护：即使空间紧凑也不切断词组"""
        from snapshow.utils import split_text_smart
        text = "人工智能"
        # 预期：限制为 3 时，不应切为 ["人工", "智能"]，而应整体推移
        segments = split_text_smart(text, max_chars=3)
        assert segments == ["人工智能"]  # 词组本身超限 4 > 3，被迫保留或按字符切

    def test_split_text_smart_punctuation_sticking(self):
        """验证标点避头：标点应粘附在前一个词末尾"""
        from snapshow.utils import split_text_smart
        text = "测试句子，非常棒。"
        # 如果 "句子" 刚好在结尾，"，" 不应出现在下一行开头
        segments = split_text_smart(text, max_chars=5)
        # ["测试句子，", "非常棒。"]
        assert "，" not in segments[1]
