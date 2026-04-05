# Snapshow 品牌定位重塑设计文档 (Repositioning Design)

> 日期：2026-04-05
> 状态：待实现
> 目标：将 snapshow 的定位从“自动化生成工具”提升为“专业的图文成片交付引擎”，强调人工编辑的掌控感与极客式的高效交付。

## 1. 品牌核心定位 (Core Positioning)

### 1.1 角色定义 (Role)
- **snapshow** 是一个 **图文成片交付引擎 (Delivery Engine)**。
- 它专注于 **“最后一公里”的工程化合成**：将创作者在外部利用 AI 工具或人工整理好的精美图片与文案，快速对齐并转化为高质量的视频成品。

### 1.2 核心价值 (Value Proposition)
- **非 AI 生成器**：snapshow 不负责产生图片或文案。它假设素材已经过人工或 AI 的深度预处理。
- **极致掌控 (Control)**：拒绝黑盒。字幕的每一处断句、语音的每一次重试、画面的每一帧转场，都在创作者的精确掌控之下。
- **极客效率 (Efficiency)**：基于 FFmpeg 的原生合成性能，配合 TUI 的极简编辑流，实现工业级的高效产出。

## 2. 文案重构策略 (Copywriting Strategy)

### 2.1 推荐工作流 (The Recommended Workflow)
1. **外部创作 (Creative Phase)**：利用 AI 工具生成图片、润色深度文案，或人工整理高质量素材。
2. **逻辑对齐 (Engineering Phase)**：通过 snapshow TUI 快速校对内容、划定分屏节奏。
3. **合成交付 (Delivery Phase)**：工业级 FFmpeg 高速合成，依靠 **8 次语音重试机制** 确保稳健交付。

### 2.2 特性话术升级 (Feature Re-framing)
- **视觉阅读节奏控制 (Smart Splitter 2.0)**：
    - **标点优先**：强制分屏，确保阅读节奏紧凑。
    - **极致洁净**：去标点化字幕，视觉美感最大化。
- **高可用音频保障 (Voice Engine)**：
    - **8 次指数退避重试**：无惧 edge-tts 网络波动，确保配音任务的连续性。
- **配置扁平化 (ProjectConfig)**：
    - 结构优化，让项目参数一目了然。

## 3. 目标受众 (Target Audience)
- 追求高产出、高质量、高标准化的 **知识博主** 与 **个人内容创作者**。
- 习惯于“AI 辅助生产素材 + 人工深度编辑”的极客玩家。

## 4. README 结构调整 (README Structure)
1. **Header**: 标题、专业的 Slogan。
2. **Vision**: 明确“交付引擎”定位，强调人机协作。
3. **Core Features**: 智能分段 2.0、语音高可用重试、FFmpeg 高速合成。
4. **Workflow**: 图示或列表说明“外部准备 -> TUI 交付”的闭环。
5. **Keybindings & Config**: 更新最新的 TUI 快捷键与扁平化配置表。

---

**预期效果**：用户不再期待“一键随机生成”，而是将其视为一个可靠的、能够提升视频精品率的专业生产力工具。
