"""CLI 入口 - 命令行界面"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import click

from .config import load_config, validate_config
from .timeline import build_timeline, print_timeline
from .user_config import (
    USER_CONFIG_PATH,
    init_user_config,
    load_user_config,
    save_user_config,
)
from .video import generate_video
from .voice import generate_voices


def setup_logging(verbose: bool = False):
    """设置日志：同时输出到控制台和文件"""
    log_level = logging.DEBUG if verbose else logging.INFO

    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清理现有的处理程序
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_format = "%H:%M:%S"
    formatter = logging.Formatter(log_format, date_format)

    # 1. 控制台处理程序
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2. 文件处理程序 (snapshow.log)
    try:
        file_handler = RotatingFileHandler("snapshow.log", maxBytes=1024 * 1024, backupCount=1, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception:
        pass


logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def main(verbose: bool):
    """snapshow - 根据图片和字幕生成配音视频"""
    setup_logging(verbose)


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="输出目录")
@click.option("--dry-run", is_flag=True, help="只显示时间线，不生成视频")
def generate(config_path: str, output: str | None, dry_run: bool):
    """根据配置文件生成视频"""
    config_path = Path(config_path)
    base_dir = config_path.parent

    logger.info(f"加载配置: {config_path}")
    config = load_config(config_path)

    if output:
        config.output_dir = output

    validate_config(config, base_dir)

    logger.info(f"项目: {config.name}")
    logger.info(f"分辨率: {config.width}x{config.height}")
    logger.info(f"图片数量: {len(config.images)}")
    logger.info(f"字幕数量: {len(config.subtitles)}")

    logger.info("生成配音...")
    from snapshow.utils import temp_work_dir

    with temp_work_dir() as audio_parent:
        audio_dir = audio_parent / "audio"
        audio_info = generate_voices(config.images, audio_dir, title=config.title, voice=config.voice, rate=config.voice_rate, volume=config.voice_volume, pitch=config.voice_pitch)

        logger.info(f"配音生成完成，共 {len(audio_info)} 条")

        logger.info("计算时间线...")
        timeline = build_timeline(
            config.images,
            config.subtitles,
            audio_info,
            config.transition_duration,
            title=config.title,
            account_name=config.account_name,
            account_id=config.account_id,
        )
        print_timeline(timeline)

        if dry_run:
            logger.info("Dry run 模式，跳过视频生成")
            return

        logger.info("开始生成视频...")
        with temp_work_dir() as work_dir:
            output_path = generate_video(config, timeline, work_dir, base_dir)
            logger.info(f"视频生成成功: {output_path}")


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def preview(config_path: str):
    """预览时间线（不生成配音和视频）"""
    config_path = Path(config_path)
    config = load_config(config_path)

    print("\n=== 配置预览 ===")
    print("(已合并用户级配置)")
    print(f"项目名称: {config.name}")
    print(f"分辨率: {config.width}x{config.height}")
    print(f"帧率: {config.fps}")
    print(f"每屏字数: {config.max_chars}")
    print(f"图片: {len(config.images)} 张")
    print(f"字幕: {len(config.subtitles)} 条")

    print("\n=== 图片列表 ===")
    for img in config.images:
        print(f"  [{img.id}] {img.path}")

    print("\n=== 字幕列表 ===")
    for sub in config.subtitles:
        print(f"  [{sub.id}] '{sub.text}' -> 图片: {sub.image}")


@main.command()
def voices():
    """列出可用的 edge-tts 语音"""
    import subprocess

    subprocess.run(["edge-tts", "--list-voices"])


@main.command()
@click.argument("path", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=".")
def ui(path: str):
    """启动 TUI 终端交互界面"""
    import os

    abs_path = os.path.abspath(path)
    os.chdir(abs_path)

    from .tui import SubtitleTUI

    app = SubtitleTUI()
    app.run()


@main.group()
def config():
    """管理用户级配置 (~/.config/snapshow/config.yaml)"""
    pass


@config.command("init")
@click.option("--force", "-f", is_flag=True, help="覆盖已有配置")
def config_init(force: bool):
    """初始化用户级配置文件"""
    if init_user_config(overwrite=force):
        logger.info(f"用户配置已创建: {USER_CONFIG_PATH}")
    else:
        logger.info(f"用户配置已存在，使用 --force 覆盖: {USER_CONFIG_PATH}")


@config.command("show")
def config_show():
    """显示当前用户级配置"""
    uc = load_user_config()
    print("\n=== 用户级配置 ===")
    print(f"配置文件: {USER_CONFIG_PATH}")
    project = uc.get("project", {})
    print("\n[项目默认]")
    print(f"  用户名:     {project.get('account_name', '(未设置)')}")
    print(f"  账号ID:     {project.get('account_id', '(未设置)')}")
    print(f"  片尾署名:   {project.get('powered_by', True)}")
    print(f"  FPS:        {project.get('fps', 30)}")
    print(f"  分辨率:     {project.get('resolution', '1080x1920')}")
    print(f"  每屏字数:   {project.get('max_chars', 10)}")
    print(f"  输出目录:   {project.get('output_dir', './output')}")
    print(f"  声音:       {project.get('voice', 'zh-CN-XiaoxiaoNeural')}")
    print(f"  语速:       {project.get('voice_rate', '+0%')}")
    print(f"  音量:       {project.get('voice_volume', '+0%')}")
    print(f"  音调:       {project.get('voice_pitch', '+0Hz')}")


@config.command("set")
@click.option("--account-name", help="默认用户名")
@click.option("--account-id", help="默认账号ID（显示时加 @）")
@click.option("--powered-by/--no-powered-by", default=None, help="是否片尾署名")
@click.option("--fps", type=int, help="默认帧率")
@click.option(
    "--resolution",
    type=str,
    help="分辨率 (如 1080x1920)",
)
@click.option("--voice", help="默认 edge-tts 声音")
@click.option("--voice-rate", help="默认语速 (如 +10%)")
@click.option("--voice-volume", help="默认音量 (如 +10%)")
@click.option("--voice-pitch", help="默认音调 (如 +10Hz)")
@click.option("--max-chars", type=int, help="默认每屏字数")
def config_set(**kwargs):
    """设置用户级配置项"""
    uc = load_user_config()
    changed = False

    if kwargs.get("account_name") is not None:
        uc.setdefault("project", {})["account_name"] = kwargs["account_name"]
        changed = True
    if kwargs.get("account_id") is not None:
        uc.setdefault("project", {})["account_id"] = kwargs["account_id"]
        changed = True
    if kwargs.get("powered_by") is not None:
        uc.setdefault("project", {})["powered_by"] = kwargs["powered_by"]
        changed = True
    if kwargs.get("fps") is not None:
        uc.setdefault("project", {})["fps"] = kwargs["fps"]
        changed = True
    if kwargs.get("resolution") is not None:
        uc.setdefault("project", {})["resolution"] = kwargs["resolution"]
        changed = True
    if kwargs.get("max_chars") is not None:
        uc.setdefault("project", {})["max_chars"] = kwargs["max_chars"]
        changed = True
    if kwargs.get("voice") is not None:
        uc.setdefault("project", {})["voice"] = kwargs["voice"]
        changed = True
    if kwargs.get("voice_rate") is not None:
        uc.setdefault("project", {})["voice_rate"] = kwargs["voice_rate"]
        changed = True
    if kwargs.get("voice_volume") is not None:
        uc.setdefault("project", {})["voice_volume"] = kwargs["voice_volume"]
        changed = True
    if kwargs.get("voice_pitch") is not None:
        uc.setdefault("project", {})["voice_pitch"] = kwargs["voice_pitch"]
        changed = True

    if changed:
        save_user_config(uc)
        logger.info("用户配置已更新")
    else:
        logger.info("未指定任何配置项，使用 --help 查看可用选项")


if __name__ == "__main__":
    main()
