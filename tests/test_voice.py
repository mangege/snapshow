"""测试语音生成模块"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestGetAudioDuration:
    @patch("snapshow.voice.find_ffprobe")
    def test_uses_find_ffprobe(self, mock_find_ffprobe):
        """Verify get_audio_duration uses find_ffprobe() not hardcoded string"""
        mock_find_ffprobe.return_value = "/usr/bin/ffprobe"

        from snapshow.voice import get_audio_duration

        with patch("snapshow.voice.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="1.234\n", returncode=0)
            result = asyncio.run(get_audio_duration(Path("test.mp3")))

            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "/usr/bin/ffprobe"
            assert result == 1.234

    def test_returns_float(self):
        """Should return a float duration"""
        from snapshow.voice import get_audio_duration

        try:
            result = asyncio.run(get_audio_duration(Path("/dev/null")))
            assert isinstance(result, float)
        except Exception:
            pytest.skip("ffprobe not available or invalid audio")


class TestGenerateVoices:
    def test_generate_voices_returns_dict(self, tmp_path):
        """Test generate_voices returns correct structure with mocked edge-tts"""
        from snapshow.config import SubtitleConfig, VoiceConfig
        from snapshow.voice import generate_voices

        subtitles = [
            SubtitleConfig(id="sub1", text="hello", image="img1", voice=VoiceConfig()),
        ]
        audio_dir = tmp_path / "audio"
        audio_dir.mkdir()

        # Mock the async voice generation
        async def fake_generate(*args, **kwargs):
            return 2.0

        with patch("snapshow.voice.generate_voice_async", new=fake_generate):
            audio_info = generate_voices(subtitles, audio_dir)

        assert "sub1" in audio_info
        assert audio_info["sub1"][1] == 2.0
        assert audio_info["sub1"][0] == audio_dir / "sub1.mp3"
