from snapshow.config import (
    ImageConfig,
    ProjectConfig,
    SubtitleConfig,
    SubtitleStyle,
    load_config,
    validate_config,
)
from snapshow.timeline import build_timeline
from snapshow.utils import find_ffmpeg, find_ffprobe, find_zh_font
from snapshow.video import generate_video
from snapshow.voice import generate_voices

try:
    from importlib.metadata import version as _version
    __version__ = _version("snapshow")
except Exception:
    __version__ = "unknown"

__all__ = [
    "ProjectConfig",
    "SubtitleConfig",
    "ImageConfig",
    "SubtitleStyle",
    "load_config",
    "validate_config",
    "build_timeline",
    "generate_video",
    "generate_voices",
    "find_ffmpeg",
    "find_ffprobe",
    "find_zh_font",
]
