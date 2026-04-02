"""测试配置解析模块"""

from pathlib import Path

import pytest
import yaml

from snapshow.config import load_config, validate_config


def create_temp_config(content: dict, tmp_path: Path) -> Path:
    """创建临时配置文件"""
    config_file = tmp_path / "test_config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(content, f, allow_unicode=True)
    return config_file


class TestLoadConfig:
    def test_load_minimal_config(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        assert config.name == "test"
        assert len(config.images) == 1
        assert len(config.subtitles) == 1
        assert config.images[0].id == "img1"
        assert config.subtitles[0].text == "hello"

    def test_load_config_with_voice(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [
                {
                    "id": "sub1",
                    "text": "hello",
                    "image": "img1",
                    "voice": {
                        "engine": "edge-tts",
                        "voice": "zh-CN-XiaoxiaoNeural",
                        "rate": "+10%",
                    },
                }
            ],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        assert config.subtitles[0].voice.voice == "zh-CN-XiaoxiaoNeural"
        assert config.subtitles[0].voice.rate == "+10%"

    def test_load_config_with_style(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
            "style": {
                "font_size": 60,
                "font_color": "yellow",
                "position": "top",
            },
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        assert config.style.font_size == 60
        assert config.style.font_color == "yellow"
        assert config.style.position == "top"


class TestValidateConfig:
    def test_valid_config(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        validate_config(config)

    def test_invalid_image_reference(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img2"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        with pytest.raises(ValueError, match="img2"):
            validate_config(config)

    def test_no_images(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [],
            "subtitles": [{"id": "sub1", "text": "hello", "image": "img1"}],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        with pytest.raises(ValueError, match="至少需要一张图片"):
            validate_config(config)

    def test_no_subtitles(self, tmp_path):
        config_data = {
            "project": {"name": "test"},
            "images": [{"id": "img1", "path": "test.jpg"}],
            "subtitles": [],
        }
        config_file = create_temp_config(config_data, tmp_path)
        config = load_config(config_file)

        with pytest.raises(ValueError, match="至少需要一条字幕"):
            validate_config(config)
