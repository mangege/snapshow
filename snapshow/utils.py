"""跨平台工具模块 - 字体搜索、FFmpeg 路径解析"""

import os
import platform
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path


def find_ffmpeg() -> str:
    """查找可用的 ffmpeg 可执行文件路径"""
    # 先尝试 PATH
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg

    system = platform.system()

    # Windows 常见安装路径
    if system == "Windows":
        search_dirs = [
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            str(Path.home() / "ffmpeg" / "bin"),
            str(Path.home() / "AppData" / "Local" / "Programs" / "ffmpeg" / "bin"),
        ]
        for d in search_dirs:
            p = Path(d) / "ffmpeg.exe"
            if p.exists():
                return str(p)

    # macOS 常见安装路径
    elif system == "Darwin":
        search_dirs = [
            "/usr/local/bin",
            "/opt/homebrew/bin",
            "/usr/bin",
            str(Path.home() / "homebrew" / "bin"),
        ]
        for d in search_dirs:
            p = Path(d) / "ffmpeg"
            if p.exists():
                return str(p)

    # Linux 额外搜索路径
    elif system == "Linux":
        search_dirs = [
            "/usr/bin",
            "/usr/local/bin",
            "/snap/bin",
            "/snap/ffmpeg/current/usr/bin",
            "/usr/lib/ffmpeg",
        ]
        for d in search_dirs:
            p = Path(d) / "ffmpeg"
            if p.exists():
                return str(p)

    return "ffmpeg"


def find_ffprobe() -> str:
    """查找可用的 ffprobe 可执行文件路径"""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        return ffprobe

    system = platform.system()
    ffmpeg_path = find_ffmpeg()

    if system == "Windows":
        base = Path(ffmpeg_path).parent
        p = base / "ffprobe.exe"
        if p.exists():
            return str(p)
    elif system in ("Darwin", "Linux"):
        base = Path(ffmpeg_path).parent
        p = base / "ffprobe"
        if p.exists():
            return str(p)

    return "ffprobe"


@lru_cache(maxsize=1)
def find_zh_font() -> str | None:
    """
    自动搜索系统中支持中文的字体。
    按优先级返回第一个找到的中文字体名称。
    """
    system = platform.system()

    # 各平台常见中文字体名称
    if system == "Windows":
        candidates = [
            "Microsoft YaHei",
            "SimHei",
            "Microsoft JhengHei",
            "SimSun",
            "KaiTi",
            "FangSong",
        ]
    elif system == "Darwin":
        candidates = [
            "PingFang SC",
            "Heiti SC",
            "STHeiti",
            "Songti SC",
            "Kaiti SC",
            "Hiragino Sans GB",
        ]
    else:  # Linux
        candidates = [
            "Noto Sans CJK SC",
            "WenQuanYi Micro Hei",
            "WenQuanYi Zen Hei",
            "Source Han Sans SC",
            "Droid Sans Fallback",
            "AR PL UMing CN",
            "AR PL UKai CN",
        ]

    for font_name in candidates:
        if _font_exists(font_name, system):
            return font_name

    return None


def _font_exists(font_name: str, system: str) -> bool:
    """检查指定字体名称在当前系统中是否存在"""
    try:
        if system == "Linux":
            result = subprocess.run(
                ["fc-match", "-f", "%{family}", font_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and font_name.lower() in result.stdout.lower()

        elif system == "Darwin":
            result = subprocess.run(
                ["system_profiler", "SPFontsDataType"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return font_name.lower() in result.stdout.lower()

        elif system == "Windows":
            import winreg

            key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        name, _, _ = winreg.EnumValue(key, i)
                        if font_name.lower() in name.lower():
                            return True
            except (FileNotFoundError, OSError):
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                        for i in range(winreg.QueryInfoKey(key)[1]):
                            name, _, _ = winreg.EnumValue(key, i)
                            if font_name.lower() in name.lower():
                                return True
                except (FileNotFoundError, OSError):
                    pass

            # fallback: 检查字体文件是否存在
            font_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
            if font_dir.exists():
                for f in font_dir.iterdir():
                    if font_name.lower() in f.name.lower():
                        return True

            return False

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return False


@contextmanager
def temp_work_dir(prefix: str = "snapshow"):
    """上下文管理器，确保临时工作目录在退出时被清理"""
    tmp = tempfile.mkdtemp(prefix=f"{prefix}_")
    try:
        yield Path(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def split_text_smart(text: str, max_chars: int) -> list[str]:
    """
    智能分段算法：
    1. 按强标点分割
    2. 对长片段使用 jieba 分词
    3. 贪婪合并并保护词组边界
    4. 标点避头（粘附在前一个词末尾）
    5. 末尾重平衡（Redistribution）
    """
    import jieba

    if not text:
        return []

    # 1. 强标点切分 (保留标点)
    # 使用正则切分，保留分隔符
    raw_parts = re.split(r"([\n。！？；])", text)
    processed_parts = []
    # 将分隔符与前一部分合并
    for i in range(0, len(raw_parts) - 1, 2):
        combined = (raw_parts[i] + raw_parts[i + 1]).strip()
        if combined:
            processed_parts.append(combined)
    if len(raw_parts) % 2 == 1:
        last_part = raw_parts[-1].strip()
        if last_part:
            processed_parts.append(last_part)

    final_segments = []
    for part in processed_parts:
        if len(part) <= max_chars:
            final_segments.append(part)
            continue

        # 2. 贪婪合并词语
        words = list(jieba.cut(part))
        consolidated_words = []
        i = 0
        while i < len(words):
            word = words[i]
            # 粘附标点
            while i + 1 < len(words) and re.match(r"^[，。！？；、,.!?;:\"')}\]]+$", words[i+1]):
                word += words[i+1]
                i += 1
            consolidated_words.append(word)
            i += 1

        sub_segments = []
        current_seg = ""
        for word in consolidated_words:
            if len(current_seg) + len(word) <= max_chars:
                current_seg += word
            else:
                if current_seg:
                    sub_segments.append(current_seg)
                
                # 处理超长词
                if len(word) > max_chars:
                    # 如果超限不多且是唯一内容，准许超限
                    if not sub_segments and len(word) <= max_chars * 1.5:
                        sub_segments.append(word)
                        current_seg = ""
                    else:
                        temp_word = word
                        while len(temp_word) > max_chars:
                            sub_segments.append(temp_word[:max_chars])
                            temp_word = temp_word[max_chars:]
                        current_seg = temp_word
                else:
                    current_seg = word
        if current_seg:
            sub_segments.append(current_seg)

        # 3. 全局重平衡：如果最后一段太短，尝试重新分配所有段落以求均衡
        if len(sub_segments) >= 2:
            last_len = len(sub_segments[-1])
            if last_len < max_chars * 0.3:
                # 尝试平分
                all_text = "".join(sub_segments)
                # 如果总长度能被更少的段落容纳，直接重新贪婪合并
                # (这里的 sub_segments 已经是贪婪的结果了，如果还是这么多段，说明必须这么多)
                
                # 重新分词并平摊到每一段
                all_words = []
                for s in sub_segments:
                    all_words.extend(list(jieba.cut(s)))
                
                # 重新根据目标平均长度合并
                avg_len = len(all_text) / len(sub_segments)
                new_sub = []
                temp_seg = ""
                for w in all_words:
                    if len(temp_seg) + len(w) <= avg_len * 1.2 and len(temp_seg) + len(w) <= max_chars:
                        temp_seg += w
                    else:
                        if temp_seg: new_sub.append(temp_seg)
                        temp_seg = w
                if temp_seg: new_sub.append(temp_seg)
                
                if len(new_sub) <= len(sub_segments) and all(len(s) <= max_chars * 1.5 for s in new_sub):
                    sub_segments = new_sub

        final_segments.extend(sub_segments)

    return final_segments
