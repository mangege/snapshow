# img2vid

根据多张图片和字幕生成配音视频的工具。

## 功能

- 多图片拼接成视频
- 自动根据字幕生成配音（edge-tts）
- 字幕与配音时间线精确对齐
- 图片间淡入淡出转场
- 可配置字幕样式

## 环境要求

- Python 3.10+
- FFmpeg（系统安装）

## 安装

### 方式一：requirements.txt（推荐）

```bash
pip install -r requirements.txt
```

### 方式二：pip 安装

```bash
pip install -e .
```

## 快速开始

### 1. 创建配置文件

```yaml
project:
  name: "my_video"
  fps: 30
  width: 1920
  height: 1080

images:
  - id: img1
    path: "images/scene1.jpg"
  - id: img2
    path: "images/scene2.jpg"

subtitles:
  - id: sub1
    text: "这是第一段字幕"
    image: img1
    voice:
      voice: zh-CN-XiaoxiaoNeural
  - id: sub2
    text: "切换到第二张图了"
    image: img2
    voice:
      voice: zh-CN-YunxiNeural

style:
  font_size: 48
  font_color: white
  position: bottom
```

### 2. 生成视频

```bash
# 方式一：使用 python -m
python -m img2vid preview project.yaml
python -m img2vid generate project.yaml

# 方式二：使用 CLI 命令（pip install -e . 后）
img2vid preview project.yaml
img2vid generate project.yaml
```

### 3. 常用命令

```bash
# 预览时间线
python -m img2vid preview project.yaml

# 生成视频
python -m img2vid generate project.yaml

# 只看时间线，不生成
python -m img2vid generate project.yaml --dry-run

# 指定输出目录
python -m img2vid generate project.yaml -o ./my_output

# 详细日志
python -m img2vid generate project.yaml -v

# 查看可用语音
python -m img2vid voices
```

## 配置说明

### 项目配置
| 字段 | 说明 | 默认值 |
|------|------|--------|
| name | 输出文件名 | output |
| fps | 帧率 | 30 |
| width | 视频宽度 | 1920 |
| height | 视频高度 | 1080 |
| output_dir | 输出目录 | ./output |
| transition_duration | 转场时长（秒） | 0.5 |

### 图片配置
| 字段 | 说明 | 必填 |
|------|------|------|
| id | 图片唯一标识 | 是 |
| path | 图片路径（相对或绝对） | 是 |
| duration | 固定时长（秒），不填则根据配音计算 | 否 |

### 字幕配置
| 字段 | 说明 | 必填 |
|------|------|------|
| id | 字幕唯一标识 | 是 |
| text | 字幕文本 | 是 |
| image | 关联的图片 ID | 是 |
| voice.engine | 语音引擎 | edge-tts |
| voice.voice | 语音角色 | zh-CN-XiaoxiaoNeural |
| voice.rate | 语速调整（如 "+10%"） | +0% |
| voice.pitch | 音调调整（如 "+10Hz"） | +0Hz |
| voice.volume | 音量调整（如 "+10%"） | +0% |

### 字幕样式
| 字段 | 说明 | 默认值 |
|------|------|--------|
| font | 字体 | Arial |
| font_size | 字号 | 48 |
| font_color | 字体颜色 | white |
| border_color | 描边颜色 | black |
| border_width | 描边宽度 | 2 |
| position | 位置（top/center/bottom） | bottom |
| margin_bottom | 底部边距 | 60 |

## 项目结构

```
img2vid/
├── img2vid/
│   ├── __init__.py
│   ├── __main__.py     # python -m 入口
│   ├── cli.py          # 命令行入口
│   ├── config.py       # 配置解析
│   ├── voice.py        # 配音生成
│   ├── timeline.py     # 时间线计算
│   └── video.py        # 视频合成
├── examples/
│   └── demo.yaml       # 示例配置
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 工作原理

1. 解析 YAML 配置文件
2. 逐条调用 edge-tts 生成配音音频
3. 根据音频时长计算每条字幕的起止时间
4. 计算每张图片的总时长（关联字幕配音时长之和）
5. 使用 FFmpeg 将图片转为视频片段，叠加字幕
6. 合并所有视频片段（带淡入淡出转场）
7. 合并所有配音音频，合成最终视频

## 开发

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check img2vid/
```

## License

MIT
