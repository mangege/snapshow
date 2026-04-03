# snapshow

根据多张图片和字幕生成短视频的自动化工具。针对短视频平台（抖音、视频号、B站等）优化，支持多种分辨率和高质量配音。

## 功能

- **交互式 TUI**：全新的终端交互界面，支持可视化编辑文案、实时分段预览（默认亮色主题）。
- **路径感知**：支持在启动时指定工作目录，所有配置和输出均基于该路径。
- **多分辨率**：支持竖屏 1080x1920/720x1280、横屏 1920x1080/1280x720、正方形 1080x1080。
- **高性能合成**：基于原生 FFmpeg 命令行，支持 GPU 硬件加速检测与自动回退。
- **自动配音**：集成 `edge-tts`，内置 10 种常用中文语音一键选择。
- **精准对齐**：字幕、音频与画面在帧级别精确同步。
- **动态转场**：支持图片间的平滑淡入淡出（xfade）。
- **个性化设置**：支持视频开头标题、结尾用户名 + @账号ID 及详细的字幕样式配置。
- **用户级配置**：通过 `Ctrl+O` 设置默认用户名、账号ID、分辨率、声音等，新项目自动继承。

## 环境要求

- Python 3.10+
- **FFmpeg**（必须在系统 PATH 中，推荐安装完整版以支持硬件加速）

## 安装

```bash
# 克隆仓库
git clone <repository-url>
cd snapshow

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
python -m snapshow ui

# 或者指定一个项目目录启动
python -m snapshow ui ./my_project
```

- **界面说明**：
    - **默认主题**：官方亮色模式 (`textual-light`)，清新稳定。
    - **左侧**：图片资源列表。
    - **中间**：直接输入文案，支持长段落自动切分。
    - **底部**：配置标题、用户名、账号ID、每屏字数、分辨率和语音。
- **核心快捷键**：
    - `Ctrl+S`: 保存配置到 `project_tui.yaml`。
    - `Ctrl+R`: **预览**生成的 YAML 配置。
    - `Ctrl+G`: **一键生成**视频（后台执行）。
    - `Ctrl+O`: 打开**用户级配置**设置默认值。
    - `Ctrl+T`: 切换亮色/深色主题。
    - `Ctrl+B`: 切换侧边栏显隐。
    - `F1`: 查看完整帮助。

### 2. 使用命令行模式

如果你已有配置文件：

```bash
# 预览时间线
python -m snapshow preview project.yaml

# 生成视频
python -m snapshow generate project.yaml
```

## 配置说明

生成的 `project_tui.yaml` 包含以下核心部分：

### 项目配置 (project)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| title | 视频开头显示的标题文字 | (空) |
| account_name | 视频结尾显示的用户名 | (空) |
| account_id | 视频结尾显示的账号ID（自动加 @ 前缀） | (空) |
| width | 视频宽度 | 1080 |
| height | 视频高度 | 1920 |
| output_dir | 输出目录 | ./output |
| transition_duration | 转场时长（秒） | 0.5 |

### 用户级配置

通过 `Ctrl+O` 或 `snapshow config set` 设置，新项目自动继承：

```bash
# 设置默认用户名和账号ID
snapshow config set --account-name 笑话小华 --account-id xiaohua123

# 设置默认分辨率和语音
snapshow config set --resolution 1080x1920 --voice zh-CN-XiaoxiaoNeural

# 查看当前配置
snapshow config show
```

## 常用命令

```bash
# 查看支持的语音角色
python -m snapshow voices

# 详细日志输出
python -m snapshow generate project.yaml -v
```

## License

MIT
