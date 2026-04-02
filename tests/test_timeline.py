"""测试时间线计算模块"""

from img2vid.config import ImageConfig, SubtitleConfig, VoiceConfig
from img2vid.timeline import build_timeline


class MockAudioInfo:
    """模拟音频信息"""
    pass


def make_image(id: str, path: str, duration: float | None = None) -> ImageConfig:
    return ImageConfig(id=id, path=path, duration=duration)


def make_subtitle(id: str, text: str, image: str, voice: str = "zh-CN-XiaoxiaoNeural") -> SubtitleConfig:
    return SubtitleConfig(
        id=id,
        text=text,
        image=image,
        voice=VoiceConfig(voice=voice),
    )


class TestBuildTimeline:
    def test_single_image_single_subtitle(self):
        images = [make_image("img1", "scene1.jpg")]
        subtitles = [make_subtitle("sub1", "hello", "img1")]
        audio_info = {"sub1": ("/path/sub1.mp3", 3.5)}

        timeline = build_timeline(images, subtitles, audio_info)

        assert len(timeline) == 1
        assert timeline[0].image_id == "img1"
        assert timeline[0].start == 0.0
        assert timeline[0].end == 3.5
        assert len(timeline[0].subtitles) == 1
        assert timeline[0].subtitles[0].text == "hello"
        assert timeline[0].subtitles[0].start == 0.0
        assert timeline[0].subtitles[0].end == 3.5

    def test_single_image_multiple_subtitles(self):
        images = [make_image("img1", "scene1.jpg")]
        subtitles = [
            make_subtitle("sub1", "hello", "img1"),
            make_subtitle("sub2", "world", "img1"),
        ]
        audio_info = {"sub1": ("/path/sub1.mp3", 2.0), "sub2": ("/path/sub2.mp3", 3.0)}

        timeline = build_timeline(images, subtitles, audio_info)

        assert len(timeline) == 1
        assert timeline[0].end == 5.0
        assert timeline[0].subtitles[0].start == 0.0
        assert timeline[0].subtitles[0].end == 2.0
        assert timeline[0].subtitles[1].start == 2.0
        assert timeline[0].subtitles[1].end == 5.0

    def test_multiple_images(self):
        images = [
            make_image("img1", "scene1.jpg"),
            make_image("img2", "scene2.jpg"),
        ]
        subtitles = [
            make_subtitle("sub1", "hello", "img1"),
            make_subtitle("sub2", "world", "img2"),
        ]
        audio_info = {"sub1": ("/path/sub1.mp3", 2.0), "sub2": ("/path/sub2.mp3", 3.0)}

        timeline = build_timeline(images, subtitles, audio_info)

        assert len(timeline) == 2
        assert timeline[0].image_id == "img1"
        assert timeline[0].start == 0.0
        assert timeline[0].end == 2.0
        assert timeline[1].image_id == "img2"
        assert timeline[1].start == 2.0
        assert timeline[1].end == 5.0

    def test_image_with_fixed_duration(self):
        images = [make_image("img1", "scene1.jpg", duration=10.0)]
        subtitles = [make_subtitle("sub1", "hello", "img1")]
        audio_info = {"sub1": ("/path/sub1.mp3", 2.0)}

        timeline = build_timeline(images, subtitles, audio_info)

        assert timeline[0].end == 10.0

    def test_image_without_subtitles(self):
        images = [
            make_image("img1", "scene1.jpg"),
            make_image("img2", "scene2.jpg"),
        ]
        subtitles = [make_subtitle("sub1", "hello", "img1")]
        audio_info = {"sub1": ("/path/sub1.mp3", 2.0)}

        timeline = build_timeline(images, subtitles, audio_info)

        assert len(timeline) == 2
        assert timeline[0].end == 2.0
        assert timeline[1].image_id == "img2"
        assert timeline[1].end == 5.0

    def test_timeline_continuity(self):
        images = [
            make_image("img1", "scene1.jpg"),
            make_image("img2", "scene2.jpg"),
            make_image("img3", "scene3.jpg"),
        ]
        subtitles = [
            make_subtitle("sub1", "first", "img1"),
            make_subtitle("sub2", "second", "img2"),
            make_subtitle("sub3", "third", "img3"),
        ]
        audio_info = {
            "sub1": ("/path/sub1.mp3", 2.0),
            "sub2": ("/path/sub2.mp3", 3.0),
            "sub3": ("/path/sub3.mp3", 2.5),
        }

        timeline = build_timeline(images, subtitles, audio_info)

        for i in range(1, len(timeline)):
            assert timeline[i].start == timeline[i-1].end
