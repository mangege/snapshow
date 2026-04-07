# snapshow —— 专业的图文成片交付引擎

## 愿景 (Vision)

`snapshow` 是一款专为追求极致效率与专业质感的创作者设计的**图文成片交付引擎**。

我们的核心理念是：**创意归于上游，交付归于 snapshow**。它并非 AI 内容生成器，而是旨在通过工程化手段，将预处理的图片与文案素材（源自 AI 工具或人工创作）高效、标准化地转化为工业级水准的短视频成片。

## 推荐工作流 (Recommended Workflow)

1. **创意阶段 (Creative Phase / 外部工具)**：利用 AI 工具生成视觉素材并精修文案，或准备高品质的人工创作资产。
2. **工程阶段 (Engineering Phase / snapshow TUI)**：使用 TUI 进行视觉节奏对齐与文案智能切分，确保画面与配音完美契合。
3. **交付阶段 (Delivery Phase / FFmpeg)**：基于工业级 FFmpeg 引擎进行自动化合成，内置 8 倍语音重试机制保障，实现高成功率的最终交付。

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

### 1. 使用 pip 安装 (推荐)

直接从 PyPI 安装最新正式版：

```bash
pip install snapshow
```

或者安装最新的开发预览版：

```bash
pip install --pre snapshow
```

### 2. 本地开发安装

如果你需要修改源码或参与开发：

```bash
# 克隆仓库
git clone https://github.com/mangege/snapshow
cd snapshow

# 创建虚拟环境并安装开发依赖
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

pip install -e ".[dev]"
```

## 快速开始

安装完成后，你可以直接使用 `snapshow` 命令。

### 1. 使用交互式界面 (推荐)

直接启动 TUI 界面进行创作：

```bash
# 在当前目录启动
snapshow ui

# 或者指定一个项目目录启动
snapshow ui ./my_project
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
snapshow preview project.yaml

# 生成视频
snapshow generate project.yaml
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
