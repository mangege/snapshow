# snapshow

根据多张图片和字幕生成短视频的自动化工具。针对短视频平台（抖音、视频号、B站等）优化，支持多种分辨率和高质量配音。

## 核心功能

- **Smart Subtitle Splitter 2.0**: 
    - **标点驱动**: 智能识别中英文标点进行自然断句。
    - **干净输出**: 自动清洗字幕中的冗余标点（保留数值小数点），使视频画面更清爽美观。
    - **语义平衡**: 基于 `jieba` 分词和 50% 长度阈值平衡算法，确保分段字数均匀且不破坏词义。
- **高可靠配音引擎**:
    - **智能重试**: 内置 8 次总尝试（1次初始请求 + 7次重试）机制。
    - **指数退避**: 采用带随机抖动（Jitter）的指数退避策略，有效应对 edge-tts API 的频率限制。
    - **实时反馈**: 重试进度和错误信息通过 TUI 通知系统实时反馈。
- **交互式 TUI**: 全新的终端交互界面，支持可视化编辑文案、实时分段预览。支持亮色/深色主题切换。
- **路径感知**: 支持在启动时指定工作目录，所有配置和输出均基于该路径。
- **高性能合成**: 基于原生 FFmpeg 命令行，支持 GPU 硬件加速检测与自动回退。
- **自动配音**: 集成 `edge-tts`，内置 10 种常用中文语音一键选择。

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

直接启动 TUI 界面进行创作：

```bash
# 在当前目录启动
python -m snapshow ui

# 或者指定一个项目目录启动
python -m snapshow ui ./my_project
```

- **核心快捷键**：
    - `Ctrl+S`: **保存**配置到 `project_tui.yaml`。
    - `Ctrl+R`: **预览**生成的 YAML 配置。
    - `Ctrl+G`: **一键生成**视频（弹出实时日志弹窗）。
    - `Ctrl+O`: 打开**用户级配置**设置默认值。
    - `Ctrl+T`: 切换**主题** (亮色/深色)。
    - `Ctrl+B`: 切换**侧边栏**显隐。
    - `Ctrl+E`: 聚焦**文案编辑器**。
    - `Ctrl+I`: 聚焦**图片列表**。
    - `F1`: 查看**完整帮助**。

### 2. 命令行模式

如果你已有配置文件：

```bash
# 预览时间线
python -m snapshow preview project.yaml

# 生成视频
python -m snapshow generate project.yaml
```

## 智能字幕示例

原始文案：
> "这款软件真的太棒了！它不仅支持自动配音，还能智能切分字幕。即便文案很长，比如这句超过了十个字，它也能处理得很好。"

**Smart Subtitle Splitter 2.0** 转换结果 (每屏限10字)：
1. `这款软件真的太棒了`
2. `它不仅支持自动配音`
3. `还能智能切分字幕`
4. `即便文案很长`
5. `比如这句超过了十个字`
6. `它也能处理得很好`

*注：输出字幕已自动去除标点，确保视频视觉美感。*

## 配置说明

### 迁移说明 (Migration Note)
从 v0.2.0 开始，配置文件结构已扁平化。原本嵌套在 `voice` 节点下的配置现已直接移至 `project` 节点下。旧版配置文件在 TUI 中保存时将自动迁移。

### 项目配置 (project)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| title | 视频开头显示的标题文字 | (空) |
| account_name | 视频结尾显示的用户名 | (空) |
| account_id | 视频结尾显示的账号ID | (空) |
| width / height | 视频分辨率宽度/高度 | 1080 / 1920 |
| max_chars | 每屏最大字符数 | 10 |
| voice | 配音角色 (如 `zh-CN-XiaoxiaoNeural`) | zh-CN-XiaoxiaoNeural |
| voice_rate | 语速 (如 `+10%`, `-5%`) | +0% |
| voice_volume | 音量 | +0% |
| voice_pitch | 音调 | +0Hz |
| transition_duration | 转场时长（秒） | 0.5 |
| powered_by | 是否显示 "Powered by snapshow" 署名 | true |
| output_dir | 输出目录 | ./output |

## 常用命令

```bash
# 查看支持的语音角色
python -m snapshow voices

# 修改全局默认设置 (用户级配置)
python -m snapshow config set --account-name 我的名字 --resolution 1080x1920
```

## License

MIT
