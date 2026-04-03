"""配置解析模块 - 解析 YAML 配置文件并验证"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .user_config import load_user_config


@dataclass
class VoiceConfig:
    engine: str = "edge-tts"
    voice: str = "zh-CN-XiaoxiaoNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"


@dataclass
class SubtitleConfig:
    id: str
    text: str
    image: str
    voice: VoiceConfig = field(default_factory=VoiceConfig)


@dataclass
class ImageConfig:
    id: str
    path: str
    duration: Optional[float] = None


@dataclass
class SubtitleStyle:
    font: str = ""  # 空字符串时自动检测中文字体
    font_size: int = 64
    font_color: str = "white"
    border_color: str = "black"
    border_width: int = 3
    position: str = "bottom"
    margin_bottom: int = 200


@dataclass
class ProjectConfig:
    name: str = "output"
    fps: int = 30
    width: int = 1080
    height: int = 1920
    images: list[ImageConfig] = field(default_factory=list)
    subtitles: list[SubtitleConfig] = field(default_factory=list)
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    transition_duration: float = 0.5
    output_dir: str = "./output"
    title: str = ""  # 视频标题，开头显示
    account_name: str = ""  # 用户名，结尾显示
    account_id: str = ""  # 账号ID，结尾显示时加 @
    powered_by: bool = True  # 是否在结尾显示 "Powered by snapshow"
    max_chars: int = 10  # 每屏字数
    max_chars: int = 10  # 每屏字数


def load_config(config_path: str | Path, use_user_config_fallback: bool = True) -> ProjectConfig:
    """加载并解析配置文件
    如果 use_user_config_fallback 为 True，则项目配置中未设置的字段会使用用户级配置
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    user_config = load_user_config() if use_user_config_fallback else None
    return _parse_config(raw, user_config)


def _parse_config(raw: dict, user_config: dict | None = None) -> ProjectConfig:
    """解析原始字典为 ProjectConfig
    user_config 提供用户级默认配置
    """
    project = raw.get("project", {})
    images_raw = raw.get("images", [])
    subtitles_raw = raw.get("subtitles", [])
    style_raw = raw.get("style", {})

    uc_project = {}
    uc_voice = {}
    if user_config:
        uc_project = user_config.get("project", {})
        uc_voice = user_config.get("voice", {})

    images = [
        ImageConfig(
            id=img["id"],
            path=img["path"],
            duration=img.get("duration"),
        )
        for img in images_raw
    ]

    subtitles = []
    for sub in subtitles_raw:
        voice_raw = sub.get("voice", {})
        voice = VoiceConfig(
            engine=voice_raw.get("engine", uc_voice.get("engine", "edge-tts")),
            voice=voice_raw.get("voice", uc_voice.get("voice", "zh-CN-XiaoxiaoNeural")),
            rate=voice_raw.get("rate", uc_voice.get("rate", "+0%")),
            volume=voice_raw.get("volume", uc_voice.get("volume", "+0%")),
            pitch=voice_raw.get("pitch", uc_voice.get("pitch", "+0Hz")),
        )
        subtitles.append(
            SubtitleConfig(
                id=sub["id"],
                text=sub["text"],
                image=sub["image"],
                voice=voice,
            )
        )

    style = SubtitleStyle(
        font=style_raw.get("font", ""),
        font_size=style_raw.get("font_size", 64),
        font_color=style_raw.get("font_color", "white"),
        border_color=style_raw.get("border_color", "black"),
        border_width=style_raw.get("border_width", 3),
        position=style_raw.get("position", "bottom"),
        margin_bottom=style_raw.get("margin_bottom", 200),
    )

    return ProjectConfig(
        name=project.get("name", uc_project.get("name", "output")),
        fps=project.get("fps", uc_project.get("fps", 30)),
        width=project.get("width", uc_project.get("width", 1080)),
        height=project.get("height", uc_project.get("height", 1920)),
        images=images,
        subtitles=subtitles,
        style=style,
        transition_duration=project.get("transition_duration", uc_project.get("transition_duration", 0.5)),
        output_dir=project.get("output_dir", uc_project.get("output_dir", "./output")),
        title=project.get("title", uc_project.get("title", "")),
        account_name=project.get("account_name", uc_project.get("account_name", "")),
        account_id=project.get("account_id", uc_project.get("account_id", "")),
        powered_by=project.get("powered_by", uc_project.get("powered_by", True)),
        max_chars=project.get("max_chars", uc_project.get("max_chars", 10)),
    )


def validate_config(config: ProjectConfig, base_dir: Path | None = None) -> None:
    """验证配置的有效性"""
    if not config.images:
        raise ValueError("至少需要一张图片")
    if not config.subtitles:
        raise ValueError("至少需要一条字幕")

    image_ids = {img.id for img in config.images}
    for sub in config.subtitles:
        if sub.image not in image_ids:
            raise ValueError(f"字幕 '{sub.id}' 引用的图片 '{sub.image}' 不存在")

    if base_dir:
        for img in config.images:
            img_path = base_dir / img.path if not Path(img.path).is_absolute() else Path(img.path)
            if not img_path.exists():
                raise FileNotFoundError(f"图片文件不存在: {img_path}")
