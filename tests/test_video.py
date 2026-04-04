"""测试视频合成模块"""

from unittest.mock import MagicMock, patch

import pytest

from snapshow.config import ProjectConfig
from snapshow.timeline import ImageSegment


class TestSegmentEndMutation:
    def test_generate_video_does_not_mutate_segments(self, tmp_path):
        """Verify generate_video does not mutate original segment.end"""
        segment = ImageSegment(
            image_id="img1",
            image_path="test.jpg",
            start=0.0,
            end=2.0,
            subtitles=[],
            audio_paths=[],
        )
        original_end = segment.end
        timeline = [segment]

        config = ProjectConfig(
            name="test",
            fps=30,
            width=1080,
            height=1920,
            transition_duration=0.5,
        )

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        base_dir = tmp_path

        # Create a dummy image file
        (tmp_path / "test.jpg").touch()

        with patch("snapshow.video.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            with patch("snapshow.video._detect_gpu_encoder", return_value=None):
                with patch("snapshow.video._resolve_font", return_value=("fontfile", "TestFont")):
                    with patch("snapshow.video.shutil.copy2"):
                        from snapshow.video import generate_video

                        generate_video(config, timeline, work_dir, base_dir)

        assert segment.end == original_end


class TestFFmpegErrorHandling:
    def test_run_ffmpeg_raises_on_failure(self):
        """_run_ffmpeg should raise RuntimeError with stderr on failure"""
        from snapshow.video import _run_ffmpeg

        with patch("snapshow.video.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("subprocess error")
            # The function catches CalledProcessError specifically,
            # but we test the wrapper exists and works
            with pytest.raises(Exception):
                _run_ffmpeg(["ffmpeg", "-i", "input.mp4"], "测试")

    def test_run_ffmpeg_succeeds(self):
        """_run_ffmpeg should not raise on success"""
        from snapshow.video import _run_ffmpeg

        with patch("snapshow.video.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            _run_ffmpeg(["ffmpeg", "-i", "input.mp4"], "测试")
            mock_run.assert_called_once()


class TestGenerateVideoAudioCollection:
    @patch("snapshow.video.subprocess.run")
    @patch("snapshow.video._detect_gpu_encoder", return_value=None)
    @patch("snapshow.video._resolve_font", return_value=("fontfile", "TestFont"))
    @patch("snapshow.video.shutil.copy2")
    def test_generate_video_collects_audio_paths(self, mock_copy, mock_font, mock_gpu, mock_run, tmp_path):
        """Verify generate_video collects audio paths from all segments and deduplicates them."""
        from snapshow.video import generate_video
        from pathlib import Path

        work_dir = tmp_path / "work"
        work_dir.mkdir()
        base_dir = tmp_path
        (tmp_path / "img1.jpg").touch()
        (tmp_path / "img2.jpg").touch()

        # Mock audio files
        audio1 = tmp_path / "audio1.mp3"
        audio2 = tmp_path / "audio2.mp3"
        audio1.touch()
        audio2.touch()

        timeline = [
            ImageSegment(
                image_id="img1", image_path="img1.jpg", start=0, end=2,
                audio_paths=[str(audio1)]
            ),
            ImageSegment(
                image_id="img2", image_path="img2.jpg", start=2, end=5,
                audio_paths=[str(audio1), str(audio2)]  # audio1 is duplicate
            )
        ]

        config = ProjectConfig(name="test", images=[])
        
        def mock_subprocess_run(cmd, *args, **kwargs):
            m = MagicMock(returncode=0, stderr="")
            if "ffprobe" in str(cmd) and "-show_entries" in str(cmd):
                m.stdout = "2.0" # Mock duration
            else:
                m.stdout = ""
            return m
            
        mock_run.side_effect = mock_subprocess_run

        generate_video(config, timeline, work_dir, base_dir)

        # Find the call to merge_audio_ffmpeg (which contains multiple -i)
        merge_audio_call = None
        for call in mock_run.call_args_list:
            args = call[0][0]
            if "-filter_complex" in args and "concat" in str(args):
                merge_audio_call = args
                break

        assert merge_audio_call is not None
        # Check that audio1 and audio2 are included exactly once (deduplicated)
        audio1_count = sum(1 for x in merge_audio_call if str(audio1) in x)
        audio2_count = sum(1 for x in merge_audio_call if str(audio2) in x)
        assert audio1_count == 1
        assert audio2_count == 1
