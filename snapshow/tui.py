import io
import logging
import re
import threading
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Static,
    TextArea,
)


class HelpScreen(ModalScreen):
    """借鉴 Harlequin 的帮助屏幕"""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help_modal {
        width: 60;
        height: auto;
        border: round $primary;
        background: $background;
        padding: 1 2;
    }
    #help_title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    #help_content {
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="help_modal"):
            yield Static("snapshow TUI 使用帮助", id="help_title")
            yield Static(
                "全局快捷键:\n"
                "  Ctrl+Q : 退出程序\n"
                "  Ctrl+S : 保存 YAML 配置\n"
                "  F3     : 预览 YAML 配置\n"
                "  Ctrl+G : 调用 FFmpeg 生成视频\n"
                "  Ctrl+T : 在 亮色/深色 主题间切换\n"
                "  Ctrl+B : 切换侧边栏显示/隐藏\n\n"
                "导航快捷键:\n"
                "  F1 : 显示此帮助\n"
                "  F2 : 聚焦 [文案编辑器]\n"
                "  F5 : 聚焦 [预览分段列表]\n"
                "  F6 : 聚焦 [图片文件列表]\n\n"
                "按任意键返回主界面",
                id="help_content",
            )

    def on_key(self) -> None:
        self.app.pop_screen()

    def on_click(self) -> None:
        self.app.pop_screen()


class PreviewConfigModal(ModalScreen):
    """预览生成的 YAML 配置文件内容"""

    CSS = """
    PreviewConfigModal {
        align: center middle;
    }
    #preview_container {
        width: 80%;
        height: 80%;
        border: round $primary;
        background: $background;
        padding: 1;
    }
    #preview_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }
    #preview_text {
        height: 1fr;
        border: none;
    }
    #close_hint {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self, content: str):
        super().__init__()
        self.content = content

    def compose(self) -> ComposeResult:
        with Vertical(id="preview_container"):
            yield Static("project_tui.yaml 预览", id="preview_title")
            ta = TextArea(self.content, language="yaml", id="preview_text")
            ta.read_only = True
            yield ta
            yield Static("按任意键返回", id="close_hint")

    def on_key(self) -> None:
        self.app.pop_screen()

    def on_click(self) -> None:
        self.app.pop_screen()


class LoadConfigModal(ModalScreen):
    """启动时询问是否加载现有配置"""

    CSS = """
    LoadConfigModal {
        align: center middle;
    }
    #modal_container {
        width: 50;
        height: auto;
        border: round $primary;
        background: $background;
        padding: 1 2;
    }
    #modal_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $text;
    }
    #modal_buttons {
        layout: horizontal;
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    Button {
        margin: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_container"):
            yield Static("检测到 project_tui.yaml 现有配置，是否加载？", id="modal_title")
            with Horizontal(id="modal_buttons"):
                yield Button("加载 (Yes)", variant="primary", id="yes")
                yield Button("清空 (No)", variant="error", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


RESOLUTION_PRESETS = [
    ("竖屏 1080x1920", (1080, 1920)),
    ("竖屏 720x1280", (720, 1280)),
    ("横屏 1920x1080", (1920, 1080)),
    ("横屏 1280x720", (1280, 720)),
    ("正方形 1080x1080", (1080, 1080)),
]


def _resolve_resolution_label(width: int, height: int) -> int:
    for i, (label, (w, h)) in enumerate(RESOLUTION_PRESETS):
        if w == width and h == height:
            return i
    return 0


class UserConfigEdit(ModalScreen):
    """编辑用户级配置"""

    CSS = """
    UserConfigEdit {
        align: center middle;
    }
    #uc_container {
        width: 80%;
        height: 80%;
        border: round $primary;
        background: $background;
        padding: 1;
    }
    #uc_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }
    #uc_scroll {
        height: 1fr;
    }
    .uc_row {
        height: auto;
        margin-bottom: 1;
    }
    .uc_row Label {
        width: 12;
        content-align: right middle;
        margin-right: 1;
    }
    .uc_row Input, .uc_row Checkbox {
        width: 1fr;
    }
    .uc_section_title {
        text-style: bold underline;
        color: $text;
        margin-top: 1;
        margin-bottom: 1;
    }
    #uc_save_btn {
        width: 100%;
        margin-top: 1;
    }
    #uc_hint {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        from .user_config import load_user_config

        uc = load_user_config()
        project = uc.get("project", {})
        voice = uc.get("voice", {})

        with Vertical(id="uc_container"):
            yield Static("用户级配置 (Ctrl+U)", id="uc_title")

            with ScrollableContainer(id="uc_scroll"):
                yield Static("项目默认设置", classes="uc_section_title")
                with Horizontal(classes="uc_row"):
                    yield Label("Logo:")
                    yield Input(value=project.get("logo", ""), placeholder="视频结尾文字", id="uc_logo_input")
                with Horizontal(classes="uc_row"):
                    yield Label("片尾署名:")
                    yield Checkbox(
                        value=project.get("powered_by", True), id="uc_powered_by", label="显示 Powered by snapshow"
                    )
                with Horizontal(classes="uc_row"):
                    yield Label("FPS:")
                    yield Input(value=str(project.get("fps", 30)), id="uc_fps_input", type="integer")
                with Horizontal(classes="uc_row"):
                    yield Label("分辨率:")
                    yield Select(
                        options=[(label, i) for i, (label, _) in enumerate(RESOLUTION_PRESETS)],
                        value=_resolve_resolution_label(project.get("width", 1080), project.get("height", 1920)),
                        id="uc_resolution_select",
                    )

                yield Static("默认声音设置", classes="uc_section_title")
                with Horizontal(classes="uc_row"):
                    yield Label("声音:")
                    yield Input(
                        value=voice.get("voice", "zh-CN-XiaoxiaoNeural"),
                        placeholder="edge-tts 声音",
                        id="uc_voice_input",
                    )
                with Horizontal(classes="uc_row"):
                    yield Label("语速:")
                    yield Input(value=voice.get("rate", "+0%"), placeholder="+0%", id="uc_rate_input")
                with Horizontal(classes="uc_row"):
                    yield Label("音量:")
                    yield Input(value=voice.get("volume", "+0%"), placeholder="+0%", id="uc_volume_input")
                with Horizontal(classes="uc_row"):
                    yield Label("音调:")
                    yield Input(value=voice.get("pitch", "+0Hz"), placeholder="+0Hz", id="uc_pitch_input")

            yield Button("保存用户配置", variant="primary", id="uc_save_btn")
            yield Static("按 Esc 取消", id="uc_hint")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "uc_save_btn":
            self.save_user_config()

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.app.pop_screen()

    def save_user_config(self) -> None:
        from .user_config import save_user_config

        res_idx = self.query_one("#uc_resolution_select", Select).value
        width, height = RESOLUTION_PRESETS[res_idx]

        config = {
            "project": {
                "logo": self.query_one("#uc_logo_input", Input).value,
                "powered_by": self.query_one("#uc_powered_by", Checkbox).value,
                "fps": int(self.query_one("#uc_fps_input", Input).value or 30),
                "width": width,
                "height": height,
            },
            "voice": {
                "engine": "edge-tts",
                "voice": self.query_one("#uc_voice_input", Input).value,
                "rate": self.query_one("#uc_rate_input", Input).value,
                "volume": self.query_one("#uc_volume_input", Input).value,
                "pitch": self.query_one("#uc_pitch_input", Input).value,
            },
        }
        save_user_config(config)
        self.notify("用户配置已保存至 ~/.config/snapshow/config.yaml", severity="information")
        self.app.pop_screen()


class UILogHandler(logging.Handler):
    """自定义日志处理器，将日志消息转发到 UI"""

    def __init__(self, log_screen):
        super().__init__()
        self.log_screen = log_screen
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        msg = self.format(record)
        if self.log_screen.log_area is not None:
            self.log_screen.app.call_from_thread(self._update_ui, msg)

    def _update_ui(self, msg):
        self.log_screen.log_buffer.write(msg + "\n")
        self.log_screen.log_area.text = self.log_screen.log_buffer.getvalue()
        self.log_screen.log_area.scroll_end(animate=False)


class GenerationLogScreen(ModalScreen):
    """视频生成日志显示弹窗"""

    CSS = """
    GenerationLogScreen {
        align: center middle;
    }
    #gen_log_container {
        width: 80%;
        height: 80%;
        border: round $primary;
        background: $background;
        padding: 1;
    }
    #gen_log_title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
        color: $primary;
    }
    #gen_log_text {
        height: 1fr;
        border: none;
        background: $surface;
    }
    #gen_log_status {
        text-align: center;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.log_buffer = io.StringIO()
        self.finished = False

    def compose(self) -> ComposeResult:
        with Vertical(id="gen_log_container"):
            yield Static("视频生成进度", id="gen_log_title")
            self.log_area = TextArea("", id="gen_log_text", read_only=True)
            yield self.log_area
            self.status_label = Static("生成中...", id="gen_log_status")
            yield self.status_label

    def set_finished(self, success: bool, message: str = ""):
        self.finished = True
        if success:
            self.status_label.update("生成完成！按任意键返回")
        else:
            self.status_label.update(f"生成失败: {message} 按任意键返回")

    def on_key(self) -> None:
        if self.finished:
            self.app.pop_screen()

    def on_click(self) -> None:
        if self.finished:
            self.app.pop_screen()


class ImageFileTree(DirectoryTree):
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [
            path
            for paths in [paths]
            for path in paths
            if not path.name.startswith(".") and (path.is_dir() or path.suffix.lower() in [".jpg", ".jpeg", ".png"])
        ]


class SubtitleTUI(App):
    sidebar_hidden = reactive(False)

    CSS = """
    /* 通用双模式适配 CSS */
    Screen {
        background: $background;
    }

    #main_container {
        layout: horizontal;
        background: $background;
    }

    /* 统一分区样式 */
    #sidebar_pane, #editor_section, #preview_section {
        border: round $panel;
        border-title-color: $text;
        border-title-style: bold;
        background: $background;
    }

    /* 聚焦状态高亮 */
    #sidebar_pane:focus-within, #editor_section:focus-within, #preview_section:focus-within {
        border: round $primary;
        border-title-color: $primary;
    }

    /* 侧边栏 */
    #sidebar_pane {
        width: 30;
        height: 100%;
        margin-right: 1;
    }
    
    ImageFileTree {
        background: $background;
        color: $text;
        border: none;
    }

    /* 右侧主面板 */
    #main_panel {
        width: 1fr;
        height: 100%;
    }

    #editor_section {
        height: 1fr;
        margin-bottom: 1;
    }

    #text_input {
        height: 1fr;
        border: none;
        background: $background;
        color: $text;
    }
    
    /* 适配双模式的光标行 */
    #text_input > .text-area--cursor-line {
        background: $surface;
    }

    /* 预览分段 */
    #preview_list {
        background: $background;
        border: none;
    }

    .segment-item {
        padding: 0 1;
        border-bottom: solid $surface;
        background: $background;
    }

    .segment-meta {
        color: $primary;
        text-style: italic;
    }

    /* 控制栏 */
    #controls {
        height: 3;
        background: $surface;
        border-top: solid $panel;
        layout: horizontal;
        padding: 0 1;
    }
    
    #controls > * {
        height: 100%;
        content-align: left middle;
        color: $text;
    }

    #char_limit {
        width: 6;
        background: $background;
        color: $text;
        border: none;
        padding: 0 1;
    }

    /* 头部与尾部 */
    Header {
        background: $primary;
        color: $background;
        text-style: bold;
    }

    Footer {
        background: $surface;
        color: $text;
    }
    #project_title_input, #project_logo_input {
        width: 15;
        height: 1;
        background: $background;
        color: $text;
        border: none;
        padding: 0 1;
        margin-right: 2;
    }
    #title_label, #logo_label, #char_limit_label {
        margin-right: 1;
        color: $text;
    }
    #char_limit {
        width: 6;
        height: 1;
        background: $background;
        color: $text;
        border: none;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出", show=True, priority=True),
        Binding("ctrl+s", "save", "保存", show=True),
        Binding("f3", "preview_config", "配置预览", show=True),
        Binding("ctrl+g", "generate", "生成", show=True),
        Binding("ctrl+t", "toggle_theme", "主题", show=True),
        Binding("ctrl+b", "toggle_sidebar", "侧边栏", show=True),
        Binding("f1", "show_help", "帮助", show=True),
        Binding("ctrl+u", "user_config", "用户配置", show=True),
        Binding("f2", "focus_editor", "编辑器", show=False),
        Binding("f5", "focus_preview", "聚焦预览", show=False),
        Binding("f6", "focus_sidebar", "资源", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.image_data = {}
        self.current_image = None
        self.max_chars = 15

    def on_mount(self) -> None:
        self.theme = "textual-light"
        self.text_area.read_only = False
        # 设置初始 border title，显示当前文件夹名
        self.query_one("#sidebar_pane").border_title = f"图片列表 ({Path.cwd().name}) [F6]"
        self.query_one("#editor_section").border_title = "内容编辑 (F2)"
        self.query_one("#preview_section").border_title = "分段预览 (F5)"

        # 动态更新 App 标题为完整路径
        self.title = f"snapshow - {Path.cwd()}"

        # 启动时检测并询问是否加载
        if Path("project_tui.yaml").exists():
            self.push_screen(LoadConfigModal(), self.handle_load_decision)
        else:
            # 没有项目配置时，使用用户级配置默认值
            self.apply_user_config_defaults()

    def apply_user_config_defaults(self):
        """应用用户级配置到 UI 字段"""
        from .user_config import load_user_config

        uc = load_user_config()
        project = uc.get("project", {})
        voice = uc.get("voice", {})
        self.query_one("#project_logo_input", Input).value = project.get("logo", "")
        self.query_one("#project_fps_input", Input).value = str(project.get("fps", 30))
        self.query_one("#project_width_input", Input).value = str(project.get("width", 1080))
        self.query_one("#project_height_input", Input).value = str(project.get("height", 1920))
        self.query_one("#default_voice_input", Input).value = voice.get("voice", "zh-CN-XiaoxiaoNeural")

    def handle_load_decision(self, should_load: bool):
        if should_load:
            self.load_initial_config()
        else:
            self.apply_user_config_defaults()
            self.notify("已开始新项目 (使用用户默认配置)")

    def load_initial_config(self):
        """尝试从 project_tui.yaml 加载配置"""
        config_path = Path("project_tui.yaml")
        if not config_path.exists():
            return

        try:
            import yaml

            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not config:
                return

            # 1. 还原项目基础信息
            project = config.get("project", {})
            self.query_one("#project_title_input", Input).value = project.get("title", "")
            self.query_one("#project_logo_input", Input).value = project.get("logo", "")

            # 2. 还原图片和字幕数据
            img_id_to_path = {img["id"]: img["path"] for img in config.get("images", [])}

            temp_image_text = {}
            for sub in config.get("subtitles", []):
                img_id = sub.get("image")
                if img_id in img_id_to_path:
                    path = img_id_to_path[img_id]
                    text = sub.get("text", "")
                    if path not in temp_image_text:
                        temp_image_text[path] = []
                    temp_image_text[path].append(text)

            for path, text_list in temp_image_text.items():
                self.image_data[path] = "，".join(text_list)

            self.notify(f"已从 {config_path} 加载现有配置")
        except Exception as e:
            self.notify(f"加载初始配置失败: {str(e)}", severity="warning")

    def action_show_help(self):
        self.push_screen(HelpScreen())

    def action_toggle_sidebar(self):
        self.sidebar_hidden = not self.sidebar_hidden

    def watch_sidebar_hidden(self, sidebar_hidden: bool) -> None:
        sidebar = self.query_one("#sidebar_pane")
        sidebar.display = not sidebar_hidden
        if sidebar_hidden and sidebar.has_focus:
            self.action_focus_editor()

    def action_focus_sidebar(self):
        if self.sidebar_hidden:
            self.action_toggle_sidebar()
        self.query_one(ImageFileTree).focus()

    def action_focus_editor(self):
        self.text_area.focus()

    def action_focus_preview(self):
        self.query_one("#preview_list").focus()

    def action_user_config(self):
        """打开用户级配置编辑界面"""
        self.push_screen(UserConfigEdit())

    def action_preview_config(self):
        """保存并预览当前的 YAML 配置"""
        self.action_save()
        config_path = Path("project_tui.yaml")
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.push_screen(PreviewConfigModal(content))
        else:
            self.notify("未找到配置文件", severity="error")

    def action_toggle_theme(self):
        """在官方亮色和深色主题间切换"""
        if self.theme == "textual-light":
            self.theme = "textual-dark"
        else:
            self.theme = "textual-light"
        self.notify(f"已切换到 {'深色' if self.theme == 'textual-dark' else '亮色'} 模式")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with Vertical(id="sidebar_pane"):
                yield ImageFileTree("./")

            with Vertical(id="main_panel"):
                # 上部：编辑区 (类似 Harlequin 的 Query Editor)
                with Vertical(id="editor_section"):
                    self.img_info = Label(" 请在左侧选择图片...")
                    yield self.img_info
                    self.text_area = TextArea(id="text_input")
                    yield self.text_area

                    with Horizontal(id="controls"):
                        yield Label("标题:", id="title_label")
                        yield Input(placeholder="视频开头文字", id="project_title_input")
                        yield Label("Logo:", id="logo_label")
                        yield Input(placeholder="视频结尾文字", id="project_logo_input")
                        yield Label("每屏字数:", id="char_limit_label")
                        yield Input(value=str(self.max_chars), id="char_limit")

                # 下部：预览区 (类似 Harlequin 的 Results Viewer)
                with Vertical(id="preview_section"):
                    self.preview_list = ListView(id="preview_list")
                    yield self.preview_list

        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = event.path
        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            self.current_image = str(path)
            self.img_info.update(f"已选中: [bold $primary]{path.name}[/]")
            self.text_area.text = self.image_data.get(self.current_image, "")
            self.refresh_preview()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self.current_image:
            self.image_data[self.current_image] = self.text_area.text
            self.refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "char_limit" and event.value.isdigit():
            self.max_chars = int(event.value)
            self.refresh_preview()

    def refresh_preview(self):
        self.preview_list.clear()
        text = self.text_area.text.strip()
        if not text:
            return

        segments = self.split_text(text, self.max_chars)

        for i, seg in enumerate(segments):
            display_text = seg
            est_duration = len(seg) * 0.25 + 0.5

            item = ListItem(
                Static(f"[b]{i + 1}.[/][segment-text] {display_text} [/] [segment-meta]({est_duration:.1f}s)[/]"),
                classes="segment-item",
            )
            self.preview_list.append(item)

    def split_text(self, text: str, max_len: int) -> list[str]:
        parts = re.split(r"[\n。！？；\n]", text)
        parts = [p.strip() for p in parts if p.strip()]

        final_segments = []
        for p in parts:
            if len(p) <= max_len:
                final_segments.append(p)
            else:
                sub_parts = re.split(r"[，、,]", p)
                current_sub = ""
                for sp in sub_parts:
                    if len(current_sub) + len(sp) <= max_len:
                        current_sub += sp + ("，" if sp != sub_parts[-1] else "")
                    else:
                        if current_sub:
                            final_segments.append(current_sub.rstrip("，"))
                        while len(sp) > max_len:
                            final_segments.append(sp[:max_len])
                            sp = sp[max_len:]
                        current_sub = sp + ("，" if sp != sub_parts[-1] else "")
                if current_sub:
                    final_segments.append(current_sub.rstrip("，"))
        return final_segments

    def action_save(self):
        """保存当前编辑内容到 YAML 配置文件"""
        if not self.image_data:
            self.notify("没有可保存的内容", severity="warning")
            return

        title = self.query_one("#project_title_input", Input).value
        logo = self.query_one("#project_logo_input", Input).value

        config_dict = {
            "project": {
                "name": "tui_project",
                "fps": 30,
                "width": 1080,
                "height": 1920,
                "output_dir": "./output",
                "title": title,
                "logo": logo,
            },
            "images": [],
            "subtitles": [],
        }

        sub_count = 1
        for img_path, text in self.image_data.items():
            if not text.strip():
                continue

            # 记录图片
            img_id = Path(img_path).stem
            config_dict["images"].append({"id": img_id, "path": img_path})

            # 切分并记录字幕
            segments = self.split_text(text, self.max_chars)
            for seg in segments:
                config_dict["subtitles"].append(
                    {
                        "id": f"sub_{sub_count:03d}",
                        "text": seg,
                        "image": img_id,
                        "voice": {"voice": "zh-CN-XiaoxiaoNeural"},
                    }
                )
                sub_count += 1

        save_path = "project_tui.yaml"
        import yaml

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, allow_unicode=True, sort_keys=False)

        self.notify(f"配置已保存至 {save_path}", severity="information")

    async def action_generate(self):
        """异步调用核心逻辑生成视频"""
        save_path = "project_tui.yaml"
        self.action_save()

        log_screen = GenerationLogScreen()
        await self.push_screen(log_screen)

        self.run_generation_task(save_path, log_screen)

    @work(thread=True)
    def run_generation_task(self, config_path: str, log_screen: GenerationLogScreen):
        """在后台线程中执行耗时的生成任务"""
        ui_handler = UILogHandler(log_screen)

        root_logger = logging.getLogger()
        root_logger.addHandler(ui_handler)
        root_logger.setLevel(logging.INFO)

        for name in ["snapshow.video", "snapshow.voice", "snapshow"]:
            logger = logging.getLogger(name)
            logger.addHandler(ui_handler)
            logger.setLevel(logging.INFO)

        try:
            import shutil
            import tempfile

            from .config import load_config, validate_config
            from .timeline import build_timeline
            from .video import generate_video
            from .voice import generate_voices

            config = load_config(config_path)
            base_dir = Path(".").resolve()
            validate_config(config, base_dir)

            # 1. 生成配音
            audio_dir = Path(tempfile.mkdtemp()) / "audio"
            audio_info = generate_voices(config.subtitles, audio_dir)

            # 2. 计算时间线
            timeline = build_timeline(
                config.images,
                config.subtitles,
                audio_info,
                config.transition_duration,
                title=config.title,
                logo=config.logo,
            )

            # 3. 生成视频
            work_dir = Path(tempfile.mkdtemp()) / "snapshow_work"
            work_dir.mkdir(parents=True, exist_ok=True)

            final_audio_dir = work_dir / "audio"
            final_audio_dir.mkdir(parents=True, exist_ok=True)
            for sub_id, (path, duration) in audio_info.items():
                new_path = final_audio_dir / path.name
                shutil.copy2(path, new_path)
                audio_info[sub_id] = (new_path, duration)

            output_path = generate_video(config, timeline, work_dir, base_dir)

            log_screen.app.call_from_thread(log_screen.set_finished, True, str(output_path))

        except Exception as e:
            log_screen.app.call_from_thread(log_screen.set_finished, False, str(e))
        finally:
            root_logger.removeHandler(ui_handler)
            for name in ["snapshow.video", "snapshow.voice", "snapshow"]:
                logging.getLogger(name).removeHandler(ui_handler)


if __name__ == "__main__":
    app = SubtitleTUI()
    app.run()
