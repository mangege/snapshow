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
    title: str = "",
    account_name: str = "",
    account_id: str = "",
) -> list[ImageSegment]:
    """
    构建完整时间线
    """
    subtitles_by_image: dict[str, list] = {}
    for sub in subtitles:
        if sub.image not in subtitles_by_image:
            subtitles_by_image[sub.image] = []
        subtitles_by_image[sub.image].append(sub)

    timeline: list[ImageSegment] = []
    current_time = 0.0

    # 1. 插入标题片段 (黑底白字，只听声音)
    if title and "__title__" in audio_info:
        audio_path, duration = audio_info["__title__"]
        sub_segment = SubtitleSegment(
            id="__title__",
            text=title,
            start=current_time,
            end=current_time + duration,
            audio_path=str(audio_path),
        )
        segment = ImageSegment(
            image_id="__title__",
            image_path="__black__",
            start=current_time,
            end=current_time + duration,
            subtitles=[sub_segment],
            audio_paths=[str(audio_path)],
        )
        timeline.append(segment)
        current_time += duration

    # 2. 插入正文图片
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

    # 3. 插入账号信息片段 (黑底白字，1s，无声)
    if account_name or account_id:
        segment = ImageSegment(
            image_id="__account__",
            image_path="__black__",
            start=current_time,
            end=current_time + 1.0,
            subtitles=[],
            audio_paths=[],
        )
        timeline.append(segment)
        current_time += 1.0

    return timeline


def print_timeline(timeline: list[ImageSegment]) -> None:
    """打印时间线供调试"""
    print("\n=== 时间线 ===")
    for seg in timeline:
        print(f"\n图片: {seg.image_id} ({seg.image_path})")
        print(f"  时间: {seg.start:.2f}s - {seg.end:.2f}s (时长: {seg.end - seg.start:.2f}s)")
        for sub in seg.subtitles:
            print(f"  字幕: '{sub.text}' [{sub.start:.2f}s - {sub.end:.2f}s]")
    print()
