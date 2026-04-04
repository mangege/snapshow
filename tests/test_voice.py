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


@pytest.mark.asyncio
async def test_generate_voice_retry_logic():
    """验证语音生成的重试逻辑、退避时长及回调触发"""
    from snapshow.voice import generate_voice_async
    from unittest.mock import patch, MagicMock
    import asyncio

    # Mock Communicate 抛出异常
    with patch("snapshow.voice.edge_tts.Communicate") as mock_comm:
        # 模拟 8 次都失败
        mock_comm.side_effect = Exception("Network Error")

        retries = []
        def on_retry(attempt, error, wait):
            retries.append((attempt, error, wait))

        # 缩短 sleep 时间并跳过实际文件删除以加速测试
        with patch("snapshow.voice.asyncio.sleep", return_value=None):
            with patch("snapshow.voice.Path.unlink", return_value=None):
                with pytest.raises(RuntimeError, match="语音生成最终失败"):
                    await generate_voice_async("test", "out.mp3", on_retry=on_retry)

        # 预期：第1次失败后重试1，第2次失败后重试2... 第7次失败后重试7。总计尝试8次。
        assert len(retries) == 7
        assert retries[0][0] == 1  # 第一次重试编号
        assert retries[-1][0] == 7 # 最后一次重试编号
        # 验证退避时间是否有指数级趋势 (2^1, 2^2...)
        assert retries[0][2] >= 1.0
        assert retries[1][2] >= 2.0
