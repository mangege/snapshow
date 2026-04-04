"""测试语音生成模块"""

import asyncio
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetAudioDuration:
    @patch("snapshow.voice.find_ffprobe")
    @pytest.mark.asyncio
    async def test_uses_find_ffprobe(self, mock_find):
        """验证使用 find_ffprobe() 而非硬编码字符串"""
        from snapshow.voice import get_audio_duration

        mock_find.return_value = "/usr/local/bin/ffprobe"
        with patch("snapshow.voice.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="2.5\n", returncode=0)
            await get_audio_duration(Path("dummy.mp3"))
            args = mock_run.call_args[0][0]
            assert args[0] == "/usr/local/bin/ffprobe"

    @pytest.mark.asyncio
    async def test_returns_float(self):
        """验证返回浮点数时长"""
        from snapshow.voice import get_audio_duration

        with patch("snapshow.voice.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="10.5\n", returncode=0)
            duration = await get_audio_duration(Path("dummy.mp3"))
            assert isinstance(duration, float)
            assert duration == 10.5


class TestGenerateVoices:
    @patch("snapshow.voice.generate_voice_async")
    def test_generate_voices_returns_dict(self, mock_gen, tmp_path):
        """测试批量生成语音返回字典"""
        from snapshow.config import ImageConfig
        from snapshow.voice import generate_voices

        # generate_voice_async 是异步的，mock 需要返回 coroutine 或使用 AsyncMock
        async def mock_async_gen(*args, **kwargs):
            return 2.0
        mock_gen.side_effect = mock_async_gen

        images = [
            ImageConfig(id="img1", path="img1.jpg", text="hello"),
        ]
        audio_dir = tmp_path
        
        # generate_voices 是同步函数
        result = generate_voices(images, audio_dir, voice="zh-CN-XiaoxiaoNeural")
        
        assert "img1" in result
        assert result["img1"][1] == 2.0
        assert result["img1"][0].name == "img1_voice.mp3"
