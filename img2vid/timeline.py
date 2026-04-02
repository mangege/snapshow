"""时间线计算模块 - 根据字幕和音频计算精确的时间线"""

from dataclasses import dataclass, field


@dataclass
class SubtitleSegment:
    id: str
    text: str
    start: float
    end: float
    audio_path: str


@dataclass
class ImageSegment:
    image_id: str
    image_path: str
    start: float
    end: float
    subtitles: list[SubtitleSegment] = field(default_factory=list)
    audio_paths: list[str] = field(default_factory=list)


def build_timeline(
    images: list,
    subtitles: list,
    audio_info: dict[str, tuple],
    transition_duration: float = 0.5,
) -> list[ImageSegment]:
    """
    构建完整时间线
    
    Args:
        images: ImageConfig 列表
        subtitles: SubtitleConfig 列表
        audio_info: {subtitle_id: (audio_path, duration)}
        transition_duration: 转场时长
        
    Returns:
        ImageSegment 列表
    """
    subtitles_by_image: dict[str, list] = {}
    for sub in subtitles:
        if sub.image not in subtitles_by_image:
            subtitles_by_image[sub.image] = []
        subtitles_by_image[sub.image].append(sub)

    timeline: list[ImageSegment] = []
    current_time = 0.0

    for img in images:
        subs = subtitles_by_image.get(img.id, [])
        if not subs:
            duration = img.duration if img.duration else 3.0
            segment = ImageSegment(
                image_id=img.id,
                image_path=img.path,
                start=current_time,
                end=current_time + duration,
            )
            timeline.append(segment)
            current_time += duration
            continue

        subtitle_segments = []
        segment_start = current_time
        audio_paths = []

        for sub in subs:
            audio_path, duration = audio_info[sub.id]
            sub_segment = SubtitleSegment(
                id=sub.id,
                text=sub.text,
                start=segment_start,
                end=segment_start + duration,
                audio_path=str(audio_path),
            )
            subtitle_segments.append(sub_segment)
            audio_paths.append(str(audio_path))
            segment_start += duration

        image_duration = segment_start - current_time

        if img.duration and img.duration > image_duration:
            image_duration = img.duration

        segment = ImageSegment(
            image_id=img.id,
            image_path=img.path,
            start=current_time,
            end=current_time + image_duration,
            subtitles=subtitle_segments,
            audio_paths=audio_paths,
        )
        timeline.append(segment)
        current_time += image_duration

    return timeline


def merge_audio_commands(timeline: list[ImageSegment], output_path: str) -> str:
    """生成 FFmpeg 合并音频的命令"""
    all_audio_paths = []
    for seg in timeline:
        all_audio_paths.extend(seg.audio_paths)

    if not all_audio_paths:
        return ""

    inputs = " ".join([f"-i '{p}'" for p in all_audio_paths])
    filter_complex = "".join([f"[{i}:a]" for i in range(len(all_audio_paths))])
    filter_complex += f"concat=n={len(all_audio_paths)}:v=0:a=1[outa]"

    return f"{inputs} -filter_complex '{filter_complex}' -map '[outa]' '{output_path}'"


def print_timeline(timeline: list[ImageSegment]) -> None:
    """打印时间线供调试"""
    print("\n=== 时间线 ===")
    for seg in timeline:
        print(f"\n图片: {seg.image_id} ({seg.image_path})")
        print(f"  时间: {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.end - seg.start:.2f}s)")
        for sub in seg.subtitles:
            print(f"  字幕: '{sub.text}' [{sub.start:.2f}s - {sub.end:.2f}s]")
    print()
