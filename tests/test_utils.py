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
