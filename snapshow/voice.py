"""配音生成模块 - 使用 edge-tts 生成语音"""

import asyncio
import logging
import random
import subprocess
import time
from pathlib import Path

import edge_tts

from .utils import find_ffprobe

logger = logging.getLogger(__name__)

MAX_RETRIES = 8  # 最大尝试次数


async def generate_voice_async(
    text: str,
    output_path: str | Path,
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    on_retry: callable = None,
) -> float:
    """
    异步生成语音文件 (带指数退避重试)

    Returns:
        音频时长（秒）
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            # 每次尝试前清理旧文件
            if output_path.exists():
                output_path.unlink()

            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)

            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    with open(output_path, "ab") as f:
                        f.write(chunk["data"])

            duration = await get_audio_duration(output_path)
            if attempt > 0:
                logger.info(f"语音生成重试成功: {output_path.name} (第 {attempt} 次重试)")
            else:
                logger.info(f"生成语音: {output_path.name}, 时长: {duration:.2f}s")
            return duration

        except Exception as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                # 计算退避时间 (指数 + 随机扰动)
                wait_time = (2**attempt) + random.random()
                error_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"语音生成失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {error_msg}。 " f"{wait_time:.1f}s 后重试..."
                )

                if on_retry:
                    try:
                        on_retry(attempt + 1, error_msg, wait_time)
                    except Exception:
                        pass  # 回调异常不应中断重试逻辑

                await asyncio.sleep(wait_time)
            else:
                logger.error(f"语音生成在 {MAX_RETRIES} 次尝试后最终失败: {str(e)}")

    raise RuntimeError(f"语音生成最终失败 ({MAX_RETRIES} 次尝试): {str(last_exception)}")


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
    images: list,
    output_dir: Path,
    title: str = "",
    voice: str = "zh-CN-XiaoxiaoNeural",
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
    on_retry: callable = None,
) -> dict[str, tuple[Path, float]]:
    """
    批量生成语音文件 (支持重试回调)

    Args:
        images: ImageConfig 列表，包含每张图的完整文本
        output_dir: 音频输出目录
        title: 标题文本，如不为空则生成 __title__ 音频
        voice: 语音名称
        rate: 语速
        volume: 音量
        pitch: 音调
        on_retry: 重试时的回调函数 (attempt, error, wait)

    Returns:
        {image_id: (audio_path, duration)}，标题为 "__title__"
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    async def _generate_all():
        tasks = []
        results = {}

        if title:
            audio_path = output_dir / "__title__.mp3"
            task = generate_voice_async(
                text=title,
                output_path=audio_path,
                voice=voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
                on_retry=on_retry,
            )
            tasks.append(("__title__", task))

        # 按图片生成语音（每张图只生成一个语音文件）
        for img in images:
            if img.text:
                audio_path = output_dir / f"{img.id}_voice.mp3"
                task = generate_voice_async(
                    text=img.text,
                    output_path=audio_path,
                    voice=voice,
                    rate=rate,
                    volume=volume,
                    pitch=pitch,
                    on_retry=on_retry,
                )
                tasks.append((img.id, task))

        for item_id, task in tasks:
            duration = await task
            if item_id == "__title__":
                audio_path = output_dir / "__title__.mp3"
            else:
                audio_path = output_dir / f"{item_id}_voice.mp3"
            results[item_id] = (audio_path, duration)
            # 每次调用后随机等待 1~3 秒，避免 edge-tts 频率限制
            sleep_time = random.uniform(1, 3)
            await asyncio.sleep(sleep_time)

        return results

    return asyncio.run(_generate_all())
