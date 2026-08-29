# ADR-002: 本地 GUI 不嵌入 Agent Runtime

- Status: Accepted
- Date: 2026-08

## Context

曾讨论在本地 RackTool APP 中加入“AI 分析”按钮，并进一步考虑 Codex App Server/Agent Runtime。

用户随后明确：

- 本项目不是商业软件；
- 使用者可以直接选择本地 APP 或 Agent Skill；
- 不希望把 Agent 套进 GUI 导致臃肿。

## Decision

V1 不在本地 GUI 内嵌：

- Codex App Server；
- Agent Runtime；
- 强制云模型调用。

本地 APP 与 Agent/Skill 通过标准文件协作：

- Analysis Package；
- Profile YAML；
- JSON；
- XLSX。

## Consequences

优点：

- GUI 轻量；
- 离线可用；
- 少一套认证和网络故障面；
- 分发简单；
- 不绑定单一 AI Provider。

代价：

- 未知格式的 Agent 辅助不是“单按钮无缝完成”；
- 用户需要导出/导入分析包或直接在 Agent 中使用 Skill。
