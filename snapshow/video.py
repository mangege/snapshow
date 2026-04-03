"""视频合成模块 - 使用 ffmpeg 命令行实现"""

import logging
import os
import platform
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
        raise RuntimeError(f"{description} 命令失败: {' '.join(cmd)}\nstderr: {e.stderr}") from e


@lru_cache(maxsize=1)
def _detect_gpu_encoder() -> str | None:
    """检测并验证可用的 GPU 硬件编码器"""
    encoders = ["h264_nvenc", "h264_vaapi", "h264_qsv", "h264_amf"]
    ffmpeg = find_ffmpeg()
    try:
        result = subprocess.run(
            [ffmpeg, "-encoders"],
            capture_output=True,
            text=True,
        )

        for enc in encoders:
            if enc in result.stdout:
                test_cmd = [
                    ffmpeg,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=black:s=64x64",
                    "-t",
                    "0.1",
                    "-c:v",
                    enc,
                    "-f",
                    "null",
                    "-",
                ]
                test_result = subprocess.run(test_cmd, capture_output=True)
                if test_result.returncode == 0:
                    logger.info(f"验证通过，使用 GPU 编码器: {enc}")
                    return enc
                else:
                    logger.warning(f"检测到 {enc} 但验证失败（可能驱动不支持），将尝试下一个...")
    except Exception:
        pass
    logger.info("未发现可用 GPU 编码器，回退至 libx264")
    return None


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
            except (FileNotFoundError, OSError):
                pass

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass

    return ("font", font_name)


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
        fontsize: int,
        fontcolor: str = "white",
        border: bool = False,
        x: str = "(w-tw)/2",
        y: str = "(h-th)/2",
        enable: str = "",
    ) -> str:
        parts = [
            f"drawtext={font_param}='{escaped_font_value}':text='{text}'",
            f"fontsize={fontsize}",
            f"fontcolor={fontcolor}",
        ]
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
        text = _escape_text(config.title)
        filters.append(_make_drawtext(text, style.font_size * 1.5))

    elif segment.image_id == "__account__":
        # 显示用户名和 @账号ID
        account_lines = []
        if config.account_name:
            account_lines.append(_escape_text(config.account_name))
        if config.account_id:
            account_lines.append(_escape_text(f"@{config.account_id}"))
        account_text = "\\n".join(account_lines)
        filters.append(_make_drawtext(account_text, style.font_size * 1.5))

        if config.powered_by:
            credits_text = _escape_text("Powered by snapshow")
            filters.append(_make_drawtext(credits_text, style.font_size * 0.6, y="(h-th)/2+(h*0.15)"))
    else:
        # 普通字幕渲染
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

            enable = f"between(t,{start},{end})"
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
    durations = []
    ffprobe = find_ffprobe()
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
    """使用 ffmpeg concat 合并音频"""
    list_file = output_path.parent / "audio_list.txt"
    with open(list_file, "w") as f:
        for p in audio_paths:
            f.write(f"file '{p.absolute()}'\n")

    ffmpeg = find_ffmpeg()
    _run_ffmpeg(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)],
        "合并音频",
    )


def generate_video(config: ProjectConfig, timeline: list[ImageSegment], work_dir: Path, base_dir: Path) -> Path:
    """
    主函数：完全使用 ffmpeg 实现视频生成
    """
    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    video_paths = []
    all_audio_paths = []

    for i, segment in enumerate(timeline):
        if i < len(timeline) - 1:
            adjusted_segment = replace(segment, end=segment.end + config.transition_duration)
        else:
            adjusted_segment = segment

        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        create_image_segment_video(adjusted_segment, config.style, config, clip_path, base_dir)
        video_paths.append(clip_path)

        for sub in segment.subtitles:
            all_audio_paths.append(Path(sub.audio_path))

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
        final_output = video_only

    # 拷贝到最终目录
    dest_path = Path(config.output_dir) / f"{config.name}.mp4"
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_output, dest_path)

    logger.info(f"视频生成完成: {dest_path}")
    return dest_path
