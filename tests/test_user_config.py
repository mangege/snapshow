"""测试用户级配置管理模块"""

from pathlib import Path

import yaml

from snapshow.user_config import (
    DEFAULT_USER_CONFIG,
    USER_CONFIG_DIR,
    USER_CONFIG_PATH,
    init_user_config,
    load_user_config,
    save_user_config,
)


class TestInitUserConfig:
    def test_init_creates_config(self, tmp_path, monkeypatch):
        """首次初始化创建默认配置"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        result = init_user_config(overwrite=True)
        assert result is True
        assert config_path.exists()

        with open(config_path, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        assert saved["project"]["fps"] == 30
        assert saved["voice"]["voice"] == "zh-CN-XiaoxiaoNeural"

    def test_init_no_overwrite_existing(self, tmp_path, monkeypatch):
        """已有配置时不覆盖"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        init_user_config(overwrite=True)
        result = init_user_config(overwrite=False)
        assert result is False

    def test_init_overwrite_existing(self, tmp_path, monkeypatch):
        """强制覆盖时重新创建"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        init_user_config(overwrite=True)
        result = init_user_config(overwrite=True)
        assert result is True


class TestLoadUserConfig:
    def test_load_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """文件不存在时返回默认配置"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        config = load_user_config()
        assert config["project"]["fps"] == 30
        assert config["voice"]["voice"] == "zh-CN-XiaoxiaoNeural"

    def test_load_reads_existing_file(self, tmp_path, monkeypatch):
        """读取已有配置"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        custom = {"project": {"fps": 60}, "voice": {"voice": "zh-CN-YunxiNeural"}}
        save_user_config(custom)

        config = load_user_config()
        assert config["project"]["fps"] == 60
        assert config["voice"]["voice"] == "zh-CN-YunxiNeural"

    def test_load_merges_partial_config(self, tmp_path, monkeypatch):
        """部分配置与默认值合并"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        partial = {"project": {"fps": 24}}
        save_user_config(partial)

        config = load_user_config()
        assert config["project"]["fps"] == 24
        assert config["project"]["width"] == 1080  # default
        assert config["voice"]["voice"] == "zh-CN-XiaoxiaoNeural"  # default


class TestSaveUserConfig:
    def test_save_creates_file(self, tmp_path, monkeypatch):
        """保存配置创建文件"""
        config_dir = tmp_path / ".config" / "snapshow"
        config_path = config_dir / "config.yaml"
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_PATH", config_path)
        monkeypatch.setattr("snapshow.user_config.USER_CONFIG_DIR", config_dir)

        save_user_config({"project": {"fps": 120}, "voice": {"voice": "test"}})
        assert config_path.exists()

        with open(config_path, "r", encoding="utf-8") as f:
            saved = yaml.safe_load(f)
        assert saved["project"]["fps"] == 120


class TestXdgCompliance:
    def test_default_path_uses_xdg(self):
        """默认路径符合 XDG 规范"""
        expected = Path.home() / ".config" / "snapshow" / "config.yaml"
        assert USER_CONFIG_PATH == expected
