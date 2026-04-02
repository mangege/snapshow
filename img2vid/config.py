"""配置解析模块 - 解析 YAML 配置文件并验证"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


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
    font: str = "Arial"
    font_size: int = 48
    font_color: str = "white"
    border_color: str = "black"
    border_width: int = 2
    position: str = "bottom"
    margin_bottom: int = 60


@dataclass
class ProjectConfig:
    name: str = "output"
    fps: int = 30
    width: int = 1920
    height: int = 1080
    images: list[ImageConfig] = field(default_factory=list)
    subtitles: list[SubtitleConfig] = field(default_factory=list)
    style: SubtitleStyle = field(default_factory=SubtitleStyle)
    transition_duration: float = 0.5
    output_dir: str = "./output"


def load_config(config_path: str | Path) -> ProjectConfig:
    """加载并解析配置文件"""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _parse_config(raw)


def _parse_config(raw: dict) -> ProjectConfig:
    """解析原始字典为 ProjectConfig"""
    project = raw.get("project", {})
    images_raw = raw.get("images", [])
    subtitles_raw = raw.get("subtitles", [])
    style_raw = raw.get("style", {})

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
            engine=voice_raw.get("engine", "edge-tts"),
            voice=voice_raw.get("voice", "zh-CN-XiaoxiaoNeural"),
            rate=voice_raw.get("rate", "+0%"),
            volume=voice_raw.get("volume", "+0%"),
            pitch=voice_raw.get("pitch", "+0Hz"),
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
        font=style_raw.get("font", "Arial"),
        font_size=style_raw.get("font_size", 48),
        font_color=style_raw.get("font_color", "white"),
        border_color=style_raw.get("border_color", "black"),
        border_width=style_raw.get("border_width", 2),
        position=style_raw.get("position", "bottom"),
        margin_bottom=style_raw.get("margin_bottom", 60),
    )

    return ProjectConfig(
        name=project.get("name", "output"),
        fps=project.get("fps", 30),
        width=project.get("width", 1920),
        height=project.get("height", 1080),
        images=images,
        subtitles=subtitles,
        style=style,
        transition_duration=project.get("transition_duration", 0.5),
        output_dir=project.get("output_dir", "./output"),
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
