# img2vid

根据多张图片和字幕生成短视频的自动化工具。针对短视频平台（抖音、视频号、B站等）优化，默认生成 9:16 竖屏视频。

## 功能

- **竖屏优先**：默认 1080x1920 分辨率，完美适配移动端。
- **高性能合成**：基于原生 FFmpeg 命令行，速度快、稳定性高，支持 GPU 加速（NVENC 等）。
- **自动配音**：集成 `edge-tts`，支持多种高质量中英文语音。
- **精准对齐**：字幕、音频与画面在帧级别精确同步，解决长视频结尾音画错位问题。
- **动态转场**：支持图片间的平滑淡入淡出（xfade）。
- **样式可调**：支持自定义字体、字号、描边及位置，默认避开短视频平台 UI 遮挡。

## 环境要求

- Python 3.10+
- **FFmpeg**（必须在系统 PATH 中，推荐安装完整版以支持更多编码器）

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd img2vid

# 创建虚拟环境并安装依赖
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

## 快速开始

### 1. 准备配置 (project.yaml)

```yaml
project:
  name: "my_video"
  width: 1080
  height: 1920

images:
  - id: img1
    path: "images/scene1.jpg"
  - id: img2
    path: "images/scene2.jpg"

subtitles:
  - id: sub1
    text: "欢迎来到竖屏短视频时代"
    image: img1
    voice:
      voice: zh-CN-XiaoxiaoNeural
  - id: sub2
    text: "基于 FFmpeg 的极速合成体验"
    image: img2
    voice:
      voice: zh-CN-YunxiNeural
```

### 2. 生成视频

```bash
# 预览时间线
python -m img2vid preview project.yaml

# 生成视频
python -m img2vid generate project.yaml
```

生成的视频将保存到 `./output/my_video.mp4`。

## 配置说明

### 项目配置 (project)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| name | 输出文件名 | output |
| fps | 帧率 | 30 |
| **width** | 视频宽度 | **1080** |
| **height** | 视频高度 | **1920** |
| output_dir | 输出目录 | ./output |
| transition_duration | 转场时长（秒） | 0.5 |

### 字幕样式 (style)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| font | 字体名称或路径 | Arial |
| **font_size** | 字号 | **64** |
| font_color | 字体颜色 | white |
| border_color | 描边颜色 | black |
| **border_width** | 描边宽度 | **3** |
| position | 位置 (top/center/bottom) | bottom |
| **margin_bottom** | 底部边距 | **200** |

## 常用命令

```bash
# 查看支持的语音角色
python -m img2vid voices

# 详细日志输出（排查问题）
python -m img2vid generate project.yaml -v

# 指定输出路径
python -m img2vid generate project.yaml -o /path/to/custom/dir
```

## 为什么选择 ffmpeg 模式？

早期的版本基于 MoviePy，但在处理长视频或多段转场时容易出现：
1. **内存泄漏**：MoviePy 缓存机制导致大项目内存占用极高。
2. **音画不同步**：随着片段增加，微小的帧差会导致结尾音频被截断。
3. **性能瓶颈**：Python 层面的图像处理远慢于原生的 FFmpeg 滤镜链。

现在的版本完全移除了 MoviePy，直接生成 FFmpeg 滤镜指令，在保证 100% 同步的同时，合成速度提升了 3-5 倍。

## License

MIT
