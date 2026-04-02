"""跨平台工具模块 - 字体搜索、FFmpeg 路径解析"""

import os
import platform
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
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
