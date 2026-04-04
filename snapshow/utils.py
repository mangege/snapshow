"""跨平台工具模块 - 字体搜索、FFmpeg 路径解析"""

import logging
import os
import platform
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


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
    1. 标点优先强制分屏 (排除小数点)
    2. 内容清洗：移除常规标点，保留数值符号和 Emoji
    3. 长句兜底：使用 jieba 和平衡算法处理超长片段
    """
    import jieba

    if not text:
        return []

    def clean_punctuation(t: str) -> str:
        """清洗标点，保留数值相关符号和表情符号"""
        # 移除常见中英文标点，但通过 lookaround 保护小数点
        # 步骤：
        # 1. 将所有点号暂时标记（如果是小数点）
        # 2. 移除所有其他标点
        # 3. 恢复小数点
        
        # 保护小数点：把数字中间的点替换为一个特殊占位符
        t = re.sub(r"(\d)\.(\d)", r"\1__DOT__\2", t)
        # 移除其余标点 (包含不再数字中间的点)
        t = re.sub(r"[，。！？；、,.!?;:\"')}\[\]]+", "", t)
        # 还原小数点
        t = t.replace("__DOT__", ".")
        return t.strip()

    # 1. 标点驱动切分
    # 匹配所有标点，但排除小数点
    # 使用正则表达式，匹配中英文停顿标点
    # 对于点号，只有当它不在两个数字之间时才作为切分点
    split_pattern = r"[，。！？；、!?;:\"')}\[\]]|\.(?!\d)|(?<!\d)\."
    raw_parts = re.split(split_pattern, text)
    
    # 清洗每个片段并过滤空值
    processed_parts = []
    for p in raw_parts:
        cleaned = clean_punctuation(p)
        if cleaned:
            processed_parts.append(cleaned)

    final_segments = []
    for part in processed_parts:
        if len(part) <= max_chars:
            final_segments.append(part)
            continue

        # 2. 对超长段落应用原有的分词合并逻辑
        words = list(jieba.cut(part))
        consolidated_words = words # 此时 part 已无标点

        sub_segments = []
        current_seg = ""
        for word in consolidated_words:
            if len(current_seg) + len(word) <= max_chars:
                current_seg += word
            else:
                if current_seg:
                    sub_segments.append(current_seg)
                
                if len(word) > max_chars:
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

        # 3. 全局重平衡
        if len(sub_segments) >= 2:
            last_len = len(sub_segments[-1])
            avg_target = sum(len(s) for s in sub_segments) / len(sub_segments)
            
            if last_len < avg_target * 0.8 or last_len < max_chars * 0.5:
                all_text = "".join(sub_segments)
                all_words = list(jieba.cut(all_text))
                target_len = len(all_text) / len(sub_segments)
                new_sub = []
                temp_seg = ""
                for w in all_words:
                    if len(temp_seg) + len(w) <= target_len * 1.2 or not temp_seg:
                        if len(temp_seg) + len(w) <= max_chars:
                            temp_seg += w
                        else:
                            if temp_seg: new_sub.append(temp_seg)
                            temp_seg = w
                    else:
                        if temp_seg: new_sub.append(temp_seg)
                        temp_seg = w
                if temp_seg: new_sub.append(temp_seg)
                
                if len(new_sub) <= len(sub_segments) and len(new_sub[-1]) > last_len:
                    sub_segments = new_sub

        final_segments.extend(sub_segments)

    return final_segments
