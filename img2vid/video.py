"""视频合成模块 - 使用 ffmpeg 命令行实现"""

import logging
import os
import shutil
import subprocess
from pathlib import Path
from .config import ProjectConfig, SubtitleStyle
from .timeline import ImageSegment, SubtitleSegment

logger = logging.getLogger(__name__)

def _detect_gpu_encoder() -> str | None:
    """检测可用的 GPU 硬件编码器"""
    encoders = ["h264_nvenc", "h264_vaapi", "h264_qsv", "h264_amf"]
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
        )
        for enc in encoders:
            if enc in result.stdout:
                logger.info(f"检测到 GPU 编码器: {enc}")
                return enc
    except FileNotFoundError:
        pass
    return None

def _resolve_font_path(font_name: str) -> str:
    """将字体名称解析为字体文件路径"""
    if Path(font_name).is_file():
        return str(Path(font_name).absolute())
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

def _escape_text(text: str) -> str:
    """转义 drawtext 滤镜中的特殊字符"""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "'\\''")
    text = text.replace(":", "\\:")
    text = text.replace(",", "\\,")
    text = text.replace("%", "\\%")
    return text

def create_image_segment_video(
    segment: ImageSegment,
    style: SubtitleStyle,
    config: ProjectConfig,
    output_path: Path,
    base_dir: Path,
) -> None:
    """使用 ffmpeg 为单个图片片段创建视频（含字幕渲染）"""
    duration = segment.end - segment.start
    fps = config.fps
    
    image_path = Path(segment.image_path)
    if not image_path.is_absolute():
        image_path = base_dir / image_path

    font_path = _resolve_font_path(style.font)
    gpu_encoder = _detect_gpu_encoder()
    codec = gpu_encoder if gpu_encoder else "libx264"

    # 滤镜链：缩放并填充到目标分辨率，确保格式为 yuv420p
    filters = [
        f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease",
        f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2:color=black",
        "format=yuv420p"
    ]

    for sub in segment.subtitles:
        start = max(0, sub.start - segment.start)
        end = sub.end - segment.start
        text = _escape_text(sub.text)
        
        # 字幕位置
        if style.position == "bottom":
            y = f"h-{style.margin_bottom}-th"
        elif style.position == "top":
            y = f"{style.margin_bottom}"
        else:
            y = "(h-th)/2"

        # 字体路径在 drawtext 中需要对冒号进行转义（Windows/Linux 兼容）
        escaped_font_path = font_path.replace(":", "\\:")
        
        drawtext = (
            f"drawtext=fontfile='{escaped_font_path}':text='{text}':"
            f"fontsize={style.font_size}:fontcolor={style.font_color}:"
            f"borderw={style.border_width}:bordercolor={style.border_color}:"
            f"x=(w-tw)/2:y={y}:enable='between(t,{start},{end})'"
        )
        filters.append(drawtext)

    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-loop", "1", "-i", str(image_path),
        "-t", f"{duration:.3f}",
        "-vf", filter_str,
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)
    logger.info(f"生成视频片段: {output_path.name}")

def merge_videos_with_xfade(
    video_paths: list[Path],
    output_path: Path,
    transition_duration: float,
    fps: int,
) -> None:
    """使用 ffmpeg xfade 滤镜合并视频并添加转场效果"""
    if len(video_paths) == 1:
        shutil.copy2(video_paths[0], output_path)
        return

    # 获取每个片段的时长
    durations = []
    for p in video_paths:
        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
            capture_output=True, text=True
        )
        durations.append(float(res.stdout.strip()))

    gpu_encoder = _detect_gpu_encoder()
    codec = gpu_encoder if gpu_encoder else "libx264"

    filter_complex = ""
    current_offset = 0.0
    
    inputs = []
    for i, p in enumerate(video_paths):
        inputs.extend(["-i", str(p)])

    for i in range(len(video_paths) - 1):
        prev_label = f"[v{i}]" if i > 0 else "[0:v]"
        next_label = f"[{i+1}:v]"
        out_label = f"[v{i+1}]"
        
        # 每一个 xfade 的 offset 是前一个片段结束的时间减去转场时间
        current_offset += durations[i] - transition_duration
        filter_complex += f"{prev_label}{next_label}xfade=transition=fade:duration={transition_duration}:offset={current_offset:.3f}"
        
        if i < len(video_paths) - 2:
            filter_complex += f"{out_label};"
        else:
            filter_complex += "[vout]"

    cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", codec,
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        str(output_path)
    ]

    subprocess.run(cmd, capture_output=True, check=True)
    logger.info(f"合并视频完成 (xfade): {output_path.name}")

def merge_audio_ffmpeg(audio_paths: list[Path], output_path: Path) -> None:
    """使用 ffmpeg concat 合并音频"""
    list_file = output_path.parent / "audio_list.txt"
    with open(list_file, "w") as f:
        for p in audio_paths:
            f.write(f"file '{p.absolute()}'\n")
    
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(output_path)
    ], capture_output=True, check=True)

def generate_video(config: ProjectConfig, timeline: list[ImageSegment], work_dir: Path, base_dir: Path) -> Path:
    """
    主函数：完全使用 ffmpeg 实现视频生成
    """
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    video_paths = []
    all_audio_paths = []

    for i, segment in enumerate(timeline):
        # 补偿转场时长（非最后一段）
        original_end = segment.end
        if i < len(timeline) - 1:
            segment.end += config.transition_duration
            
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        create_image_segment_video(segment, config.style, config, clip_path, base_dir)
        video_paths.append(clip_path)
        
        # 收集音频
        for sub in segment.subtitles:
            all_audio_paths.append(Path(sub.audio_path))
        
        # 还原 segment 以免影响后续
        segment.end = original_end

    # 1. 合并视频流
    video_only = work_dir / "video_only.mp4"
    merge_videos_with_xfade(video_paths, video_only, config.transition_duration, config.fps)

    # 2. 合并音频流
    if all_audio_paths:
        audio_only = work_dir / "audio_only.mp3"
        merge_audio_ffmpeg(all_audio_paths, audio_only)
        
        # 3. 最终封装
        output_name = f"{config.name}.mp4"
        final_output = work_dir / output_name
        
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_only), "-i", str(audio_only),
            "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
            str(final_output)
        ], capture_output=True, check=True)
    else:
        final_output = video_only

    # 拷贝到最终目录
    dest_path = Path(config.output_dir) / f"{config.name}.mp4"
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_output, dest_path)

    logger.info(f"视频生成完成: {dest_path}")
    return dest_path
