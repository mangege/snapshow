"""视频合成模块 - 使用 FFmpeg 合成最终视频"""

import logging
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from .config import ProjectConfig, SubtitleStyle
from .timeline import ImageSegment, SubtitleSegment

logger = logging.getLogger(__name__)


def _get_image_dimensions(image_path: Path) -> tuple[int, int]:
    with Image.open(image_path) as img:
        return img.size


def _scale_image_to_fit(image_path: Path, width: int, height: int) -> Path:
    """缩放图片以适配目标分辨率，保持比例"""
    img = Image.open(image_path)
    img_ratio = img.width / img.height
    target_ratio = width / height

    if img_ratio > target_ratio:
        new_width = int(height * img_ratio)
        new_height = height
    else:
        new_width = width
        new_height = int(width / img_ratio)

    output = Path(tempfile.mkdtemp()) / f"scaled_{image_path.name}"
    output.parent.mkdir(parents=True, exist_ok=True)

    img_resized = img.resize((new_width, new_height), Image.LANCZOS)
    img_resized.save(output)
    return output


def _escape_subtitle_text(text: str) -> str:
    """转义 FFmpeg drawtext 特殊字符"""
    text = text.replace("'", r"'\''")
    text = text.replace(":", r"\:")
    text = text.replace(",", r"\,")
    text = text.replace("[", r"\[")
    text = text.replace("]", r"\]")
    text = text.replace("%", r"\%")
    return text


def _build_subtitle_filter(
    sub: SubtitleSegment,
    style: SubtitleStyle,
    video_width: int,
    video_height: int,
    global_offset: float = 0.0,
) -> str:
    """构建单条字幕的 drawtext 滤镜"""
    escaped_text = _escape_subtitle_text(sub.text)

    start = sub.start - global_offset
    end = sub.end - global_offset

    if style.position == "bottom":
        y = f"h - {style.margin_bottom} - th"
    elif style.position == "top":
        y = style.margin_bottom
    else:
        y = "(h - th) / 2"

    return (
        f"drawtext="
        f"text='{escaped_text}':"
        f"fontfile={style.font}:"
        f"fontsize={style.font_size}:"
        f"fontcolor={style.font_color}:"
        f"borderw={style.border_width}:"
        f"bordercolor={style.border_color}:"
        f"x=(w - tw) / 2:"
        f"y={y}:"
        f"enable='between(t\\,{start}\\,{end})'"
    )


def create_image_video(
    segment: ImageSegment,
    config: ProjectConfig,
    output_path: Path,
) -> None:
    """为单个图片片段创建视频（含字幕）"""
    duration = segment.end - segment.start

    image_path = Path(segment.image_path)
    if not image_path.is_absolute():
        image_path = Path.cwd() / image_path

    scaled_path = _scale_image_to_fit(image_path, config.width, config.height)

    subtitle_filters = []
    for sub in segment.subtitles:
        filter_str = _build_subtitle_filter(
            sub, config.style, config.width, config.height, segment.start
        )
        subtitle_filters.append(filter_str)

    vf_parts = []
    vf_parts.append(
        f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease,"
        f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2:black"
    )
    if subtitle_filters:
        vf_parts.extend(subtitle_filters)

    vf = ",".join(vf_parts)

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(scaled_path),
        "-f", "lavfi",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]

    logger.debug(f"运行命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"创建视频片段: {output_path.name} ({duration:.2f}s)")


def merge_videos(
    video_paths: list[Path],
    output_path: Path,
    transition_duration: float = 0.5,
) -> None:
    """合并多个视频片段，添加转场效果"""
    if len(video_paths) == 1:
        import shutil
        shutil.copy2(video_paths[0], output_path)
        return

    inputs = []
    for vp in video_paths:
        inputs.extend(["-i", str(vp)])

    n = len(video_paths)
    xfade_offset = 0.0

    first_seg_duration_cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_paths[0]),
    ]
    result = subprocess.run(first_seg_duration_cmd, capture_output=True, text=True, check=True)

    filter_parts = []
    current_input = 0

    for i in range(1, n):
        prev_label = f"v{current_input}" if current_input > 0 else "[0:v]"
        curr_input = f"[{i}:v]"
        out_label = f"v{current_input + 1}" if i < n - 1 else "vout"

        filter_parts.append(
            f"{prev_label}{curr_input}"
            f"xfade=transition=fade:duration={transition_duration}:offset={xfade_offset}"
            f"{out_label}"
        )

        seg_duration_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_paths[i]),
        ]
        result = subprocess.run(seg_duration_cmd, capture_output=True, text=True, check=True)
        seg_duration = float(result.stdout.strip())

        xfade_offset += seg_duration - transition_duration
        current_input += 1

    audio_parts = []
    for i in range(n):
        audio_parts.append(f"[{i}:a]")
    audio_parts.append(f"concat=n={n}:v=0:a=1[aout]")
    audio_filter = "".join(audio_parts)

    full_filter = ";".join(filter_parts) + ";" + audio_filter

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", full_filter,
        "-map", "vout",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]

    logger.debug(f"运行命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"合并视频完成: {output_path}")


def add_audio_to_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    """将音频轨道替换到视频中"""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        str(output_path),
    ]

    logger.debug(f"运行命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f"添加音频完成: {output_path}")


def generate_video(config: ProjectConfig, timeline: list[ImageSegment], work_dir: Path) -> Path:
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
        create_image_video(segment, config, clip_path)
        video_paths.append(clip_path)
        all_audio_paths.extend(segment.audio_paths)

    if all_audio_paths:
        merged_audio = audio_dir / "merged_audio.aac"
        inputs = " ".join([f"-i '{p}'" for p in all_audio_paths])
        concat_parts = "".join([f"[{i}:a]" for i in range(len(all_audio_paths))])
        filter_complex = f"{concat_parts}concat=n={len(all_audio_paths)}:v=0:a=1[outa]"

        cmd = f"ffmpeg -y {inputs} -filter_complex '{filter_complex}' -map '[outa]' -c:a aac -b:a 192k '{merged_audio}'"
        subprocess.run(cmd, shell=True, check=True, capture_output=True)

        video_with_subtitles = work_dir / "video_with_subtitles.mp4"
        merge_videos(video_paths, video_with_subtitles, config.transition_duration)

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
