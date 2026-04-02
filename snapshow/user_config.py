"""用户级配置管理 - 存储在 ~/.config/snapshow/config.yaml (XDG 规范)"""

import os
from pathlib import Path

import yaml

# 遵循 XDG Base Directory 规范
_XDG_CONFIG_HOME = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
USER_CONFIG_DIR = Path(_XDG_CONFIG_HOME) / "snapshow"
USER_CONFIG_PATH = USER_CONFIG_DIR / "config.yaml"

DEFAULT_USER_CONFIG = {
    "project": {
        "logo": "",
        "powered_by": True,
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "output_dir": "./output",
    },
    "voice": {
        "engine": "edge-tts",
        "voice": "zh-CN-XiaoxiaoNeural",
        "rate": "+0%",
        "volume": "+0%",
        "pitch": "+0Hz",
    },
}


def get_user_config_path() -> Path:
    """返回用户配置文件路径"""
    return USER_CONFIG_PATH


def load_user_config() -> dict:
    """加载用户配置，如果不存在则返回默认配置"""
    if USER_CONFIG_PATH.exists():
        with open(USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)
            if user_config:
                return _merge_defaults(user_config)
    return DEFAULT_USER_CONFIG.copy()


def save_user_config(config: dict) -> None:
    """保存用户配置"""
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def init_user_config(overwrite: bool = False) -> bool:
    """初始化用户配置文件
    如果文件已存在且 overwrite=False，则不覆盖
    """
    if USER_CONFIG_PATH.exists() and not overwrite:
        return False

    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(DEFAULT_USER_CONFIG, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return True


def _merge_defaults(user_config: dict) -> dict:
    """将用户配置与默认配置合并，确保所有必需字段存在"""
    merged = DEFAULT_USER_CONFIG.copy()
    if "project" in user_config:
        merged["project"].update(user_config["project"])
    if "voice" in user_config:
        merged["voice"].update(user_config["voice"])
    return merged
