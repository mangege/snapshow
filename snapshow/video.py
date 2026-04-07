"""视频合成模块 - 使用 ffmpeg 命令行实现"""

import logging
import os
import platform
import re
import shutil
import subprocess
from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from .config import ProjectConfig, SubtitleStyle
from .timeline import ImageSegment
from .utils import find_ffmpeg, find_ffprobe, find_zh_font

logger = logging.getLogger(__name__)


def _run_ffmpeg(cmd: list[str], description: str = "FFmpeg") -> None:
    """运行 FFmpeg 命令，失败时抛出带上下文的异常"""
    try:
        subprocess.run(cmd, capture_output=True, check=True, text=True)
    except subprocess.CalledProcessError as e:
        full_cmd = " ".join(cmd)
        logger.error(f"{description} 执行失败!\n命令: {full_cmd}\n错误输出: {e.stderr}", exc_info=True)
        raise RuntimeError(f"{description} 命令失败: {full_cmd}\nstderr: {e.stderr}") from e


@lru_cache(maxsize=1)
def _resolve_font(font_name: str) -> tuple[str, str]:
    """将字体名称解析为 ffmpeg drawtext 可用的字体参数
    返回 (param_name, param_value)，param_name 为 'font' 或 'fontfile'
    .ttc 文件使用 font= 让 ffmpeg 通过 fontconfig 查找
    如果字体名为空，自动搜索系统中支持中文的字体
    """
    system = platform.system()

    # 自动检测中文字体
    if not font_name or font_name.strip() == "":
        font_name = find_zh_font()
        if font_name:
            logger.info(f"自动检测到中文字体: {font_name}")
        else:
            logger.warning("未找到中文字体，中文可能显示为方块")
            font_name = "Arial"

    if Path(font_name).is_file():
        ext = Path(font_name).suffix.lower()
        if ext == ".ttc":
            return ("font", font_name)
        return ("fontfile", str(Path(font_name).absolute()))

    try:
        if system == "Linux":
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", font_name],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            font_file = result.stdout.strip()
            if font_file.endswith(".ttc"):
                return ("font", font_name)
            return ("fontfile", font_file)

        elif system == "Darwin":
            result = subprocess.run(
                ["system_profiler", "SPFontsDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if font_name.lower() in result.stdout.lower():
                return ("font", font_name)

        elif system == "Windows":
            import winreg

            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, value, _ = winreg.EnumValue(key, i)
                        if font_name.lower() in name.lower():
                            font_file = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / value
                            if font_file.suffix.lower() == ".ttc":
                                return ("font", font_name)
                            return ("fontfile", str(font_file))
            except (FileNotFoundError, OSError) as e:
                logger.debug(f"Windows 注册表字体查询异常: {e}", exc_info=True)

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError) as e:
        logger.debug(f"字体解析过程异常: {e}", exc_info=True)

    return ("font", font_name)


def _escape_text(text: str) -> str:
    """
    针对 FFmpeg drawtext 滤镜精修文本转义。
    适用于单引号包裹的情况。
    """
    if not text:
        return ""
    # 1. 基础转义：反斜杠和单引号
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    # 2. 扩展转义：百分号 (针对 expansion=normal)
    text = text.replace("%", "%%")
    return text


@lru_cache(maxsize=1)
def _detect_gpu_encoder() -> str | None:
    """检测可用的 GPU 编码器
    按优先级检测：nvidia -> qsv -> vaapi -> amd -> none
    返回编码器名称 or None（使用 CPU）
    """
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        return None

    try:
        result = subprocess.run(
            [ffmpeg, "-encoders"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return None

        encoders = result.stdout

        if "h264_nvenc" in encoders:
            logger.info("GPU encoder detected: h264_nvenc")
            return "h264_nvenc"
        if "h264_qsv" in encoders:
            logger.info("GPU encoder detected: h264_qsv")
            return "h264_qsv"
        if "h264_vaapi" in encoders:
            logger.info("GPU encoder detected: h264_vaapi")
            return "h264_vaapi"
        if "h264_amf" in encoders:
            logger.info("GPU encoder detected: h264_amf")
            return "h264_amf"
        if "h264_videotoolbox" in encoders:
            logger.info("GPU encoder detected: h264_videotoolbox")
            return "h264_videotoolbox"

    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.debug(f"GPU 编码器检测过程异常: {e}", exc_info=True)

    logger.info("No GPU encoder detected, using CPU encoding")
    return None


def create_image_segment_video(
    segment: ImageSegment,
    style: SubtitleStyle,
    config: ProjectConfig,
    output_path: Path,
    base_dir: Path,
    work_dir: Path,
) -> None:
    """使用 ffmpeg 为单个图片片段创建视频（含字幕渲染）"""
    duration = segment.end - segment.start
    fps = config.fps

    # 基础输入处理
    if segment.image_path == "__black__":
        input_args = ["-f", "lavfi", "-i", f"color=black:s={config.width}x{config.height}:r={fps}"]
    else:
        image_path = Path(segment.image_path)
        if not image_path.is_absolute():
            image_path = base_dir / image_path
        input_args = ["-framerate", str(fps), "-loop", "1", "-i", str(image_path)]

    font_param, font_value = _resolve_font(style.font)
    gpu_encoder = _detect_gpu_encoder()
    codec = gpu_encoder if gpu_encoder else "libx264"

    # 安全边距：抖音会裁切四周（左右 2-3%，上下 5-10%）
    # 画面缩小到 88% 宽、82% 高，四周留黑边让平台裁切
    safe_w = int(config.width * 0.88)
    safe_h = int(config.height * 0.82)

    # 滤镜链
    filters = []
    if segment.image_path != "__black__":
        filters.extend(
            [
                f"scale={config.width}:{config.height}:force_original_aspect_ratio=decrease",
                f"pad={config.width}:{config.height}:(ow-iw)/2:(oh-ih)/2:color=black",
            ]
        )
    filters.append("format=yuv420p")

    escaped_font_value = font_value.replace(":", "\\:")

    def _make_drawtext(
        text: str,
        fontsize: float,
        fontcolor: str = "white",
        border: bool = False,
        x: str = "(w-text_w)/2",
        y: str = "(h-text_h)/2",
        enable: str = "",
        text_align: str = "",
        is_file: bool = False,
    ) -> str:
        # 如果是文件路径，使用 textfile 参数
        text_param = f"textfile='{text}'" if is_file else f"text='{text}'"
        
        parts = [
            f"drawtext={font_param}='{escaped_font_value}':{text_param}",
            f"fontsize={fontsize}",
            f"fontcolor={fontcolor}",
        ]
        if text_align:
            parts.append(f"text_align={text_align}")
        if border:
            parts.extend(
                [
                    f"borderw={style.border_width}",
                    f"bordercolor={style.border_color}",
                ]
            )
        parts.extend([f"x={x}", f"y={y}"])
        if enable:
            parts.append(f"enable='{enable}'")
        return ":".join(parts)

    # 特殊处理标题和账号
    if segment.image_id == "__title__":
        title_text = segment.subtitles[0].text if segment.subtitles else config.title
        # 彻底解决换行符方块问题：按行拆分，生成多个独立 drawtext 滤镜
        lines = title_text.split("\n")
        total_lines = len(lines)
        line_height = style.font_size * 1.8 # 估算行高，包含行间距
        
        for i, line in enumerate(lines):
            # 精准计算每一行的 y 坐标，实现整体居中
            # 逻辑：起始 y = 屏幕中心 - 总高度的一半 + 当前行的偏移
            y_offset = (i - (total_lines - 1) / 2) * line_height
            y_formula = f"(h-text_h)/2 + {y_offset}"
            
            text = _escape_text(line)
            if text:
                filters.append(_make_drawtext(text, style.font_size * 1.5, y=y_formula))

    elif segment.image_id == "__account__":
        # 显示用户名和 @账号ID（两个独立 drawtext，避免换行符转义问题）
        # 安全区位置：底部偏上
        if config.account_name:
            filters.append(_make_drawtext(_escape_text(config.account_name), style.font_size * 1.5, y="h*0.35"))
        if config.account_id:
            filters.append(_make_drawtext(_escape_text(f"@{config.account_id}"), style.font_size * 1.5, y="h*0.45"))

        if config.powered_by:
            credits_text = _escape_text("Powered by snapshow")
            filters.append(_make_drawtext(credits_text, style.font_size * 0.6, y="h*0.65"))
    else:
        # 普通字幕渲染（安全区内，单行显示）
        for sub in segment.subtitles:
            start = max(0, sub.start - segment.start)
            end = sub.end - segment.start
            enable = f"between(t,{start},{end})"

            text = _escape_text(sub.text)
            y = "h*0.78"
            filters.append(_make_drawtext(text, style.font_size, style.font_color, border=True, y=y, enable=enable))

    filter_str = ",".join(filters)

    ffmpeg = find_ffmpeg()
    cmd = (
        [ffmpeg, "-y"]
        + input_args
        + [
            "-t",
            f"{duration:.3f}",
            "-vf",
            filter_str,
            "-c:v",
            codec,
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            str(output_path),
        ]
    )

    _run_ffmpeg(cmd, "创建视频片段")
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
    ffprobe = find_ffprobe()
    if not ffprobe:
        raise RuntimeError("ffprobe not found")

    ffprobe = find_ffprobe()
    if not ffprobe:
        raise RuntimeError("ffprobe not found")

    durations = []
    for p in video_paths:
        res = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(p),
            ],
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(f"Failed to get duration for {p}: {res.stderr}")
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
        next_label = f"[{i + 1}:v]"
        out_label = f"[v{i + 1}]"

        # 每一个 xfade 的 offset 是前一个片段结束的时间减去转场时间
        current_offset += durations[i] - transition_duration
        xfade_str = f"xfade=transition=fade:duration={transition_duration}:offset={current_offset:.3f}"
        filter_complex += f"{prev_label}{next_label}{xfade_str}"

        if i < len(video_paths) - 2:
            filter_complex += f"{out_label};"
        else:
            filter_complex += "[vout]"

    ffmpeg = find_ffmpeg()
    cmd = (
        [ffmpeg, "-y"]
        + inputs
        + [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-c:v",
            codec,
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "fast",
            str(output_path),
        ]
    )

    _run_ffmpeg(cmd, "合并视频(xfade)")
    logger.info(f"合并视频完成 (xfade): {output_path.name}")


def merge_audio_ffmpeg(audio_paths: list[Path], output_path: Path) -> None:
    """使用 ffmpeg concat 滤镜无缝合并音频"""
    if len(audio_paths) == 1:
        shutil.copy2(audio_paths[0], output_path)
        return

    ffmpeg = find_ffmpeg()
    inputs = []
    for p in audio_paths:
        inputs.extend(["-i", str(p)])

    filter_parts = []
    for i in range(len(audio_paths)):
        filter_parts.append(f"[{i}:a]")
    filter_str = "".join(filter_parts) + f"concat=n={len(audio_paths)}:v=0:a=1[aout]"

    cmd = [ffmpeg, "-y"] + inputs + ["-filter_complex", filter_str, "-map", "[aout]", str(output_path)]
    _run_ffmpeg(cmd, "合并音频")


def generate_video(config: ProjectConfig, timeline: list[ImageSegment], work_dir: Path, base_dir: Path) -> Path:
    """
    主函数：完全使用 ffmpeg 实现视频生成
    """
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    video_paths = []
    all_audio_paths = []
    seen_audio = set()

    for i, segment in enumerate(timeline):
        if i < len(timeline) - 1:
            adjusted_segment = replace(segment, end=segment.end + config.transition_duration)
        else:
            adjusted_segment = segment

        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        create_image_segment_video(adjusted_segment, config.style, config, clip_path, base_dir, work_dir)
        video_paths.append(clip_path)

        # 收集音频路径并去重，保持顺序
        for ap in segment.audio_paths:
            p = Path(ap)
            if p not in seen_audio:
                all_audio_paths.append(p)
                seen_audio.add(p)

    # 1. 合并视频流
    video_only = work_dir / "video_only.mp4"
    merge_videos_with_xfade(video_paths, video_only, config.transition_duration, config.fps)

    # 2. 合并音频流
    if all_audio_paths:
        audio_only = work_dir / "audio_only.mp3"
        merge_audio_ffmpeg(all_audio_paths, audio_only)

    # 3. 最终封装
    # 优先使用 title 作为文件名，若为空则回退到 name
    base_name = config.title.strip() if config.title else config.name
    # 过滤掉不合法的路径字符
    output_name = re.sub(r'[\\/*?:"<>|]', "", base_name)
    if not output_name:
        output_name = config.name
    output_name += ".mp4"
    
    final_output = work_dir / output_name

    if all_audio_paths:
        audio_only = work_dir / "audio_only.mp3"
        merge_audio_ffmpeg(all_audio_paths, audio_only)

        ffmpeg = find_ffmpeg()
        _run_ffmpeg(
            [
                ffmpeg,
                "-y",
                "-i",
                str(video_only),
                "-i",
                str(audio_only),
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                str(final_output),
            ],
            "最终封装",
        )
    else:
        # 重命名 video_only 为目标名称
        video_only.rename(final_output)

    # 拷贝到最终目录
    dest_path = Path(config.output_dir) / output_name
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_output, dest_path)

    logger.info(f"视频生成完成: {dest_path}")
    return dest_path
