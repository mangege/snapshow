"""CLI 入口 - 命令行界面"""

import logging
import tempfile
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def main():
    """snapshow - 根据图片和字幕生成配音视频"""
    pass


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), default=None, help="输出目录")
@click.option("--dry-run", is_flag=True, help="只显示时间线，不生成视频")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def generate(config_path: str, output: str | None, dry_run: bool, verbose: bool):
    """根据配置文件生成视频"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

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
    audio_dir = Path(tempfile.mkdtemp()) / "audio"
    audio_info = generate_voices(config.subtitles, audio_dir)

    # 生成标题语音
    if config.title:
        import asyncio

        from .voice import generate_voice_async

        title_audio_path = audio_dir / "__title__.mp3"
        duration = asyncio.run(
            generate_voice_async(text=config.title, output_path=title_audio_path, voice="zh-CN-XiaoxiaoNeural")
        )
        audio_info["__title__"] = (title_audio_path, duration)

    logger.info(f"配音生成完成，共 {len(audio_info)} 条")

    logger.info("计算时间线...")
    timeline = build_timeline(
        config.images, config.subtitles, audio_info, config.transition_duration, title=config.title, logo=config.logo
    )
    print_timeline(timeline)

    if dry_run:
        logger.info("Dry run 模式，跳过视频生成")
        return

    logger.info("开始生成视频...")
    work_dir = Path(tempfile.mkdtemp()) / "snapshow_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 将音频拷贝到工作目录
    final_audio_dir = work_dir / "audio"
    final_audio_dir.mkdir(parents=True, exist_ok=True)
    for sub_id, (path, duration) in audio_info.items():
        import shutil

        new_path = final_audio_dir / path.name
        shutil.copy2(path, new_path)
        audio_info[sub_id] = (new_path, duration)

    output_path = generate_video(config, timeline, work_dir, base_dir)

    logger.info(f"视频生成成功: {output_path}")


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def preview(config_path: str):
    """预览时间线（不生成配音和视频）"""
    config_path = Path(config_path)
    config = load_config(config_path)

    print("\n=== 配置预览 ===")
    print(f"(已合并用户级配置)")
    print(f"项目名称: {config.name}")
    print(f"分辨率: {config.width}x{config.height}")
    print(f"帧率: {config.fps}")
    print(f"图片: {len(config.images)} 张")
    print(f"字幕: {len(config.subtitles)} 条")

    print("\n=== 图片列表 ===")
    for img in config.images:
        print(f"  [{img.id}] {img.path}")

    print("\n=== 字幕列表 ===")
    for sub in config.subtitles:
        print(f"  [{sub.id}] '{sub.text}' -> 图片: {sub.image}, 语音: {sub.voice.voice}")


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
    voice = uc.get("voice", {})
    print(f"\n[项目默认]")
    print(f"  Logo:       {project.get('logo', '(未设置)')}")
    print(f"  片尾署名:   {project.get('powered_by', True)}")
    print(f"  FPS:        {project.get('fps', 30)}")
    print(f"  分辨率:     {project.get('width', 1080)}x{project.get('height', 1920)}")
    print(f"  输出目录:   {project.get('output_dir', './output')}")
    print(f"\n[声音默认]")
    print(f"  声音:       {voice.get('voice', 'zh-CN-XiaoxiaoNeural')}")
    print(f"  语速:       {voice.get('rate', '+0%')}")
    print(f"  音量:       {voice.get('volume', '+0%')}")
    print(f"  音调:       {voice.get('pitch', '+0Hz')}")


@config.command("set")
@click.option("--logo", help="默认 Logo 文字")
@click.option("--powered-by/--no-powered-by", default=None, help="是否片尾署名")
@click.option("--fps", type=int, help="默认帧率")
@click.option(
    "--resolution",
    type=click.Choice(["9:16", "16:9", "1:1", "4:3", "3:4"]),
    help="分辨率比例",
)
@click.option("--voice", help="默认 edge-tts 声音")
@click.option("--rate", help="默认语速 (如 +10%)")
@click.option("--volume", help="默认音量 (如 +10%)")
@click.option("--pitch", help="默认音调 (如 +10Hz)")
def config_set(**kwargs):
    """设置用户级配置项"""
    uc = load_user_config()
    changed = False

    if kwargs.get("logo") is not None:
        uc.setdefault("project", {})["logo"] = kwargs["logo"]
        changed = True
    if kwargs.get("powered_by") is not None:
        uc.setdefault("project", {})["powered_by"] = kwargs["powered_by"]
        changed = True
    if kwargs.get("fps") is not None:
        uc.setdefault("project", {})["fps"] = kwargs["fps"]
        changed = True
    if kwargs.get("resolution") is not None:
        res_map = {
            "9:16": (1080, 1920),
            "16:9": (1920, 1080),
            "1:1": (1080, 1080),
            "4:3": (1280, 960),
            "3:4": (960, 1280),
        }
        w, h = res_map[kwargs["resolution"]]
        uc.setdefault("project", {})["width"] = w
        uc.setdefault("project", {})["height"] = h
        changed = True
    if kwargs.get("voice") is not None:
        uc.setdefault("voice", {})["voice"] = kwargs["voice"]
        changed = True
    if kwargs.get("rate") is not None:
        uc.setdefault("voice", {})["rate"] = kwargs["rate"]
        changed = True
    if kwargs.get("volume") is not None:
        uc.setdefault("voice", {})["volume"] = kwargs["volume"]
        changed = True
    if kwargs.get("pitch") is not None:
        uc.setdefault("voice", {})["pitch"] = kwargs["pitch"]
        changed = True

    if changed:
        save_user_config(uc)
        logger.info("用户配置已更新")
    else:
        logger.info("未指定任何配置项，使用 --help 查看可用选项")


if __name__ == "__main__":
    main()
