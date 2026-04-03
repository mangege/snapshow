"""配音生成模块 - 使用 edge-tts 生成语音"""

import asyncio
import logging
import subprocess
from pathlib import Path

import edge_tts

from .utils import find_ffprobe

logger = logging.getLogger(__name__)


async def generate_voice_async(
    text: str,
    output_path: str | Path,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> float:
    """
    异步生成语音文件

    Returns:
        音频时长（秒）
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 先删除旧文件（如果存在）
    if output_path.exists():
        output_path.unlink()

    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            with open(output_path, "ab") as f:
                f.write(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            pass

    duration = await get_audio_duration(output_path)
    logger.info(f"生成语音: {output_path.name}, 时长: {duration:.2f}s")
    return duration


async def get_audio_duration(audio_path: Path) -> float:
    """获取音频文件时长（秒）"""
    ffprobe_path = find_ffprobe()

    result = subprocess.run(
        [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def generate_voices(
    subtitles: list,
    output_dir: Path,
    title: str = "",
    title_voice: VoiceConfig | None = None,
) -> dict[str, tuple[Path, float]]:
    """
    批量生成语音文件

    Args:
        subtitles: SubtitleConfig 列表
        output_dir: 音频输出目录
        title: 标题文本，如不为空则生成 __title__ 音频
        title_voice: 标题语音配置，默认使用第一条字幕的语音

    Returns:
        {subtitle_id: (audio_path, duration)}
    """
    from .config import VoiceConfig

    output_dir.mkdir(parents=True, exist_ok=True)

    if title_voice is None and subtitles:
        title_voice = subtitles[0].voice
    elif title_voice is None:
        title_voice = VoiceConfig()

    async def _generate_all():
        tasks = []
        results = {}

        if title:
            audio_path = output_dir / "__title__.mp3"
            task = generate_voice_async(
                text=title,
                output_path=audio_path,
                voice=title_voice.voice,
                rate=title_voice.rate,
                volume=title_voice.volume,
                pitch=title_voice.pitch,
            )
            tasks.append(("__title__", task))

        for i, sub in enumerate(subtitles):
            audio_path = output_dir / f"{sub.id}.mp3"
            task = generate_voice_async(
                text=sub.text,
                output_path=audio_path,
                voice=sub.voice.voice,
                rate=sub.voice.rate,
                volume=sub.voice.volume,
                pitch=sub.voice.pitch,
            )
            tasks.append((sub.id, task))

        for sub_id, task in tasks:
            duration = await task
            audio_path = output_dir / f"{sub_id}.mp3"
            results[sub_id] = (audio_path, duration)

        return results

    return asyncio.run(_generate_all())
