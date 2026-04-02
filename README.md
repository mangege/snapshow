# img2vid

根据多张图片和字幕生成短视频的自动化工具。针对短视频平台（抖音、视频号、B站等）优化，默认生成 9:16 竖屏视频。

## 功能

- **交互式 TUI**：全新的终端交互界面，支持可视化编辑文案、实时分段预览（默认亮色主题）。
- **路径感知**：支持在启动时指定工作目录，所有配置和输出均基于该路径。
- **竖屏优先**：默认 1080x1920 分辨率，完美适配移动端。
- **高性能合成**：基于原生 FFmpeg 命令行，支持 GPU 硬件加速检测与自动回退。
- **自动配音**：集成 `edge-tts`，支持多种高质量中英文语音。
- **精准对齐**：字幕、音频与画面在帧级别精确同步。
- **动态转场**：支持图片间的平滑淡入淡出（xfade）。
- **个性化设置**：支持视频开头标题、结尾 Logo 及详细的字幕样式配置。

## 环境要求

- Python 3.10+
- **FFmpeg**（必须在系统 PATH 中，推荐安装完整版以支持硬件加速）

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

### 1. 使用交互式界面 (推荐)

最简单的方式是直接启动 TUI 界面进行创作：

```bash
# 在当前目录启动
python -m img2vid ui

# 或者指定一个项目目录启动
python -m img2vid ui ./my_project
```

- **界面说明**：
    - **默认主题**：官方亮色模式 (`textual-light`)，清新稳定。
    - **左侧**：图片资源列表。
    - **中间**：直接输入文案，支持长段落自动切分。
    - **底部**：配置标题、Logo 及字数限制。
- **核心快捷键**：
    - `Ctrl+S`: 保存配置到 `project_tui.yaml`。
    - `F3`: **预览**生成的 YAML 配置。
    - `Ctrl+G`: **一键生成**视频（后台执行）。
    - `Ctrl+T`: 切换亮色/深色主题。
    - `Ctrl+B`: 切换侧边栏显隐。
    - `F1`: 查看完整帮助。

### 2. 使用命令行模式

如果你已有配置文件：

```bash
# 预览时间线
python -m img2vid preview project.yaml

# 生成视频
python -m img2vid generate project.yaml
```

## 配置说明

生成的 `project_tui.yaml` 包含以下核心部分：

### 项目配置 (project)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| title | 视频开头显示的标题文字 | (空) |
| logo | 视频结尾显示的 Logo 文字 | (空) |
| output_dir | 输出目录 | ./output |
| transition_duration | 转场时长（秒） | 0.5 |

## 常用命令

```bash
# 查看支持的语音角色
python -m img2vid voices

# 详细日志输出
python -m img2vid generate project.yaml -v
```

## License

MIT
