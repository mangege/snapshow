import re
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
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
            yield Static("img2vid TUI 使用帮助", id="help_title")
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
                id="help_content"
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
        self.text_area.read_only = False
        # 设置初始 border title，显示当前文件夹名
        self.query_one("#sidebar_pane").border_title = f"图片列表 ({Path.cwd().name}) [F6]"
        self.query_one("#editor_section").border_title = "内容编辑 (F2)"
        self.query_one("#preview_section").border_title = "分段预览 (F5)"

        # 动态更新 App 标题为完整路径
        self.title = f"img2vid - {Path.cwd()}"

        # 启动时检测并询问是否加载
        if Path("project_tui.yaml").exists():
            self.push_screen(LoadConfigModal(), self.handle_load_decision)

    def handle_load_decision(self, should_load: bool):
        if should_load:
            self.load_initial_config()
        else:
            self.notify("已开始新项目 (未加载配置)")

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
        self.action_save()  # 生成前先保存最新状态

        self.notify("正在后台生成视频，请稍候...", severity="information", timeout=10)
        self.run_generation_task(save_path)

    @work(thread=True)
    def run_generation_task(self, config_path: str):
        """在后台线程中执行耗时的生成任务"""
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
            work_dir = Path(tempfile.mkdtemp()) / "img2vid_work"
            work_dir.mkdir(parents=True, exist_ok=True)

            final_audio_dir = work_dir / "audio"
            final_audio_dir.mkdir(parents=True, exist_ok=True)
            for sub_id, (path, duration) in audio_info.items():
                new_path = final_audio_dir / path.name
                shutil.copy2(path, new_path)
                audio_info[sub_id] = (new_path, duration)

            output_path = generate_video(config, timeline, work_dir, base_dir)
            self.notify(f"视频生成成功！\n保存至: {output_path}", severity="information", timeout=15)

        except Exception as e:
            self.notify(f"生成失败: {str(e)}", severity="error", timeout=20, markup=False)


if __name__ == "__main__":
    app = SubtitleTUI()
    app.run()
