# ADR-004: 通过 Profile 扩展陌生布局，而非堆硬编码

- Status: Accepted
- Date: 2026-08

## Context

不同项目的 XLSX 机柜图排版差异明显。直接在 Parser 中写大量“某客户/某列/某 Sheet 特例”会快速失控。

## Decision

建立 YAML Profile 机制：

- 描述 U 轴、机柜标题、设备区域、方向、忽略文本等；
- Profile 可由人工或 Agent 生成；
- RackCore 必须 Validate；
- Profile 可提交 Git 共享；
- 通用 Parser + Profile 优先于客户硬编码。

## Consequences

优点：

- 一次适配，多次复用；
- 便于 Agent 辅助；
- Git 可审计；
- 减少 Parser 特例。

代价：

- 需要 schema、matcher、validator；
- Profile 设计过度复杂时需要主动收敛。
