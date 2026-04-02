from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Header, Footer, DirectoryTree, Static, Input, Label, ListItem, ListView, TextArea, Checkbox
from textual.binding import Binding
from pathlib import Path
import re

class ImageFileTree(DirectoryTree):
    def filter_paths(self, paths: list[Path]) -> list[Path]:
        return [path for paths in [paths] for path in paths if not path.name.startswith(".") and (path.is_dir() or path.suffix.lower() in [".jpg", ".jpeg", ".png"])]

class SubtitleTUI(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #main_container {
        layout: horizontal;
    }
    #sidebar {
        width: 30;
        height: 100%;
        border-right: solid $primary;
    }
    #content {
        width: 1fr;
        height: 100%;
        padding: 1;
    }
    .section-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        margin-bottom: 1;
    }
    #text_input {
        height: 10;
        border: tall $accent;
        margin-bottom: 1;
    }
    #controls {
        height: 3;
        align: middle left;
    }
    #char_limit {
        width: 10;
    }
    #preview_list {
        border: solid $primary;
        height: 1fr;
        overflow-y: scroll;
    }
    .segment-item {
        padding: 0 1;
        border-bottom: solid $surface;
    }
    .segment-text {
        color: $text;
    }
    .segment-meta {
        color: $text-muted;
        text-style: italic;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "退出", show=True),
        Binding("ctrl+s", "save", "保存 YAML", show=True),
        Binding("ctrl+g", "generate", "生成视频", show=True),
    ]

    def __init__(self):
        super().__init__()
        self.image_data = {} # {path: text}
        self.current_image = None
        self.max_chars = 15 # 每屏最大字数

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main_container"):
            with Vertical(id="sidebar"):
                yield Label(" [图片列表] ", classes="section-title")
                yield ImageFileTree("./")
            
            with Vertical(id="content"):
                yield Label(" [当前图片] ", classes="section-title")
                self.img_info = Label("请在左侧选择图片...")
                yield self.img_info
                
                yield Label(" [输入文案] (支持长段落，自动切分) ", classes="section-title")
                self.text_area = TextArea(id="text_input")
                yield self.text_area
                
                with Horizontal(id="controls"):
                    yield Checkbox("过滤标点符号", value=True, id="filter_punc")
                    yield Label("  每屏字数限制: ")
                    yield Input(value=str(self.max_chars), id="char_limit")

                yield Label(" [预览分段] ", classes="section-title")
                self.preview_list = ListView(id="preview_list")
                yield self.preview_list
                
        yield Footer()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        path = event.path
        if path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            self.current_image = str(path)
            self.img_info.update(f"已选中: [bold $accent]{path.name}[/]")
            # 加载已存在的文字
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

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        self.refresh_preview()

    def refresh_preview(self):
        self.preview_list.clear()
        text = self.text_area.text.strip()
        if not text:
            return

        filter_punc = self.query_one("#filter_punc").value
        segments = self.split_text(text, self.max_chars)
        
        for i, seg in enumerate(segments):
            display_text = seg
            if filter_punc:
                # 简单过滤常见标点
                display_text = re.sub(r'[，。！？；、,.!?\\-;]', '', seg)
            
            # 模拟估算时长 (大约 1个字 0.25s)
            est_duration = len(seg) * 0.25 + 0.5
            
            item = ListItem(
                Static(f"[b]{i+1}.[/][segment-text] {display_text} [/] [segment-meta]({est_duration:.1f}s)[/]"),
                classes="segment-item"
            )
            self.preview_list.append(item)

    def split_text(self, text: str, max_len: int) -> list[str]:
        # 1. 先按显式换行和强标点拆分
        parts = re.split(r'[\n。！？；\n]', text)
        parts = [p.strip() for p in parts if p.strip()]
        
        final_segments = []
        for p in parts:
            if len(p) <= max_len:
                final_segments.append(p)
            else:
                # 2. 长句按逗号或字数强行切分
                sub_parts = re.split(r'[，、,]', p)
                current_sub = ""
                for sp in sub_parts:
                    if len(current_sub) + len(sp) <= max_len:
                        current_sub += sp + ("，" if sp != sub_parts[-1] else "")
                    else:
                        if current_sub:
                            final_segments.append(current_sub.rstrip("，"))
                        # 如果单个子句就超过了 max_len，暴力按字数切
                        while len(sp) > max_len:
                            final_segments.append(sp[:max_len])
                            sp = sp[max_len:]
                        current_sub = sp + ("，" if sp != sub_parts[-1] else "")
                if current_sub:
                    final_segments.append(current_sub.rstrip("，"))
        return final_segments

    def action_save(self):
        self.notify("正在保存配置到 project_tui.yaml...", severity="information")
        # 这里以后可以实现真实的 YAML 导出逻辑

    def action_generate(self):
        self.notify("准备调用 FFmpeg 生成视频...", severity="warning")

if __name__ == "__main__":
    app = SubtitleTUI()
    app.run()
