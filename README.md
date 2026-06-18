# code-flow-map

把一段代码逻辑追踪成一张**可点击的交互式数据流图**——业务流程做骨架，点任意节点就能看它的
输入/输出结构与数据的来源/去向。产物是一个自包含 HTML（手绘草图风），比 mermaid 表达力强。

这是给 Claude Code / 各类 coding agent 用的 **skill**：你只要说「帮我看下 X 的逻辑」，
它就去读代码、产出这张图。

## 能干什么

- **看懂一条链路**：追踪某段逻辑 / 函数 / 命令 / 管线，画成分组化的流程骨架。
- **点节点看 I/O**：右侧面板展示该节点的输入/输出结构（JSON、库表、结构体、文件均可），并标来源与去向。
- **全局数据流向**：选中节点，高亮它的全部上游来源与下游去向，跟着数据走。
- **重构对比**：旧 ↔ 新双架构并排，节点一一对应、互不污染，附迁移计划。

## 安装

需要 Node。用 [skills](https://github.com/obra/skills) 一键安装到你的 agent skills 目录：

```bash
npx skills add Blushyes/code-flow-map
```

装好后，在 Claude Code / 支持 skills 的 agent 里直接说：

> 帮我看下 创建订单接口 的逻辑

## 本地开发

skill 内容都在 [`skill/`](skill/) 下。直接渲染一份 spec 试试：

```bash
python3 skill/scripts/build_flow.py <spec.json> out.html
```
