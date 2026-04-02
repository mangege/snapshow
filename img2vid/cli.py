"""CLI 入口 - 命令行界面"""

import logging
import tempfile
from pathlib import Path

import click

from .config import load_config, validate_config
from .timeline import build_timeline, print_timeline
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
    """img2vid - 根据图片和字幕生成配音视频"""
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
    logger.info(f"配音生成完成，共 {len(audio_info)} 条")

    logger.info("计算时间线...")
    timeline = build_timeline(config.images, config.subtitles, audio_info, config.transition_duration)
    print_timeline(timeline)

    if dry_run:
        logger.info("Dry run 模式，跳过视频生成")
        return

    logger.info("开始生成视频...")
    work_dir = Path(tempfile.mkdtemp()) / "img2vid_work"
    output_path = generate_video(config, timeline, work_dir)

    logger.info(f"视频生成成功: {output_path}")


@main.command()
@click.argument("config_path", type=click.Path(exists=True))
def preview(config_path: str):
    """预览时间线（不生成配音和视频）"""
    config_path = Path(config_path)
    config = load_config(config_path)

    print("\n=== 配置预览 ===")
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


if __name__ == "__main__":
    main()
