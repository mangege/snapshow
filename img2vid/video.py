"""视频合成模块 - 使用 MoviePy 合成最终视频"""

import logging
import subprocess
from pathlib import Path

from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_audioclips,
    concatenate_videoclips,
    vfx,
)

from .config import ProjectConfig, SubtitleStyle
from .timeline import ImageSegment, SubtitleSegment

logger = logging.getLogger(__name__)


def _resolve_font_path(font_name: str) -> str:
    """将字体名称解析为字体文件路径"""
    if Path(font_name).is_file():
        return font_name
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", font_name],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return font_name


def _create_subtitle_clip(
    sub: SubtitleSegment,
    style: SubtitleStyle,
    video_width: int,
    video_height: int,
    global_offset: float = 0.0,
) -> TextClip:
    """创建单条字幕的 TextClip"""
    start = sub.start - global_offset
    end = sub.end - global_offset
    duration = end - start

    font_path = _resolve_font_path(style.font)

    text_clip = TextClip(
        text=sub.text,
        font=font_path,
        font_size=style.font_size,
        color=style.font_color,
        stroke_color=style.border_color,
        stroke_width=style.border_width,
        transparent=True,
        duration=duration,
    ).with_start(start)

    if style.position == "bottom":
        y = video_height - style.margin_bottom - text_clip.size[1]
    elif style.position == "top":
        y = style.margin_bottom
    else:
        y = (video_height - text_clip.size[1]) / 2

    return text_clip.with_position(("center", y))

    if style.position == "bottom":
        y = video_height - style.margin_bottom - text_clip.size[1]
    elif style.position == "top":
        y = style.margin_bottom
    else:
        y = (video_height - text_clip.size[1]) / 2

    return text_clip.with_position(("center", y))


def create_image_video(
    segment: ImageSegment,
    config: ProjectConfig,
    output_path: Path,
    base_dir: Path,
) -> None:
    """为单个图片片段创建视频（含字幕）"""
    duration = segment.end - segment.start

    image_path = Path(segment.image_path)
    if not image_path.is_absolute():
        image_path = base_dir / image_path

    clip = ImageClip(str(image_path)).with_duration(duration)

    clip = clip.with_effects([vfx.Resize((config.width, config.height))])

    clips_to_composite = [clip]

    for sub in segment.subtitles:
        sub_clip = _create_subtitle_clip(
            sub, config.style, config.width, config.height, segment.start
        )
        clips_to_composite.append(sub_clip)

    if len(clips_to_composite) > 1:
        final_clip = CompositeVideoClip(clips_to_composite, size=(config.width, config.height))
    else:
        final_clip = clip

    final_clip.write_videofile(
        str(output_path),
        fps=config.fps,
        codec="libx264",
        preset="fast",
        audio=False,
        logger=None,
    )
    logger.info(f"创建视频片段: {output_path.name} ({duration:.2f}s)")


def merge_videos(
    video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.5,
    fps: int = 30,
) -> None:
    """合并多个视频片段，添加转场效果"""
    if len(video_paths) == 1:
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return

    clips = [VideoFileClip(str(p)) for p in video_paths]

    clips_with_transition = []
    for i, clip in enumerate(clips):
        if i > 0:
            clip = clip.with_effects([vfx.CrossFadeIn(transition_duration)])
        if i < len(clips) - 1:
            clip = clip.with_effects([vfx.CrossFadeOut(transition_duration)])
        clips_with_transition.append(clip)

    final_clip = concatenate_videoclips(
        clips_with_transition,
        method="compose",
        padding=-transition_duration,
    )

    final_clip.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        preset="fast",
        logger=None,
    )

    for clip in clips:
        clip.close()

    logger.info(f"合并视频完成: {output_path}")


def add_audio_to_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    """将音频轨道替换到视频中"""
    video = VideoFileClip(str(video_path))
    audio = AudioFileClip(str(audio_path))

    final_clip = video.with_audio(audio)
    final_clip.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        logger=None,
    )

    video.close()
    audio.close()
    logger.info(f"添加音频完成: {output_path}")


def generate_video(config: ProjectConfig, timeline: list[ImageSegment], work_dir: Path, base_dir: Path) -> Path:
    """
    主函数：根据配置和时间线生成最终视频
    
    Returns:
        输出视频路径
    """
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    video_paths = []
    all_audio_paths = []

    for i, segment in enumerate(timeline):
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        create_image_video(segment, config, clip_path, base_dir)
        video_paths.append(clip_path)
        all_audio_paths.extend(segment.audio_paths)

    if all_audio_paths:
        merged_audio = audio_dir / "merged_audio.aac"
        audio_clips = [AudioFileClip(str(p)) for p in all_audio_paths]
        merged_audio_clip = concatenate_audioclips(audio_clips)
        merged_audio_clip.write_audiofile(str(merged_audio), codec="aac", logger=None)
        for ac in audio_clips:
            ac.close()

        video_with_subtitles = work_dir / "video_with_subtitles.mp4"
        merge_videos(video_paths, video_with_subtitles, config.transition_duration, config.fps)

        output_path = work_dir / f"{config.name}.mp4"
        add_audio_to_video(video_with_subtitles, merged_audio, output_path)
    else:
        output_path = work_dir / f"{config.name}.mp4"
        merge_videos(video_paths, output_path, config.transition_duration)

    import shutil
    output_final = Path(config.output_dir) / f"{config.name}.mp4"
    output_final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, output_final)

    logger.info(f"视频生成完成: {output_final}")
    return output_final
