# Snapshow TUI 内置图片预览设计文档

> 日期：2026-04-05
> 状态：待实现
> 目标：在 TUI 的左侧边栏增加一个基于 ANSI 字符渲染的图片预览区域，实现“点击即看图”的沉浸式校对体验。

## 1. 核心技术 (Core Technology)

### 1.1 字符渲染引擎 (ANSI Image Renderer)
- **依赖库**：`Pillow` (PIL) 进行图像缩放和像素处理。
- **渲染方案**：将 RGB 像素映射到 ANSI 256 色。
- **布局匹配**：
    - **预览尺寸**：约 30x30 字符（竖屏）或 40x20 字符（横屏），根据侧边栏宽度动态适配。
    - **采样策略**：使用双线性插值降采样，确保缩略图轮廓清晰。

### 1.2 异步加载机制 (Async Loading)
- **Textual Worker**：使用 `@work` 在后台线程执行图像到 ANSI 字符串的转换。
- **缓存层 (Caching)**：引入 `lru_cache` 缓存已生成的预览字符串，避免重复渲染带来的性能开销。
- **UI 占位符**：在加载期间显示 `[italic]Rendering...[/]`。

## 2. UI 布局重构 (UI Layout)

- **ID: `#sidebar_pane` (Vertical Container)**
    - **Top (70%)**: `ImageFileTree` (现有的图片列表)。
    - **Bottom (30%)**: `Static#thumbnail_preview` (新增的预览窗口)。
    - **样式**：增加 `border: round $primary;` 边框，使其与整体设计风格统一。

## 3. 交互流程 (Interaction Flow)

1. **触发**：用户在 `ImageFileTree` 中点击一个 `.jpg`/`.png` 文件。
2. **信号处理**：`on_directory_tree_file_selected` 接收路径，并向 `thumbnail_preview` 发送渲染请求。
3. **渲染与更新**：后台线程完成转换后，通过 `app.call_from_thread` 安全地更新预览窗口的 `.update()`。

## 4. 示例展示 (Visual Concept)

```text
+-----------------+---------------------+
| [图片列表]       | [文案编辑区]         |
| image1.jpg      |                     |
| image2.jpg      |                     |
| ...             |                     |
+-----------------+                     |
| [预览图]         |                     |
|  ########       |                     |
|  ##  ##  ##     |                     |
|  ########       |                     |
+-----------------+---------------------+
```

---

**预期效果**：通过 ANSI 渲染，创作者可以在不离开终端的情况下，瞬间确认图片的构图和基本色调，实现极致的极客校对流。
