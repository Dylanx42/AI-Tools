# ADR-003: V1 聚焦 XLSX 单元格/合并单元格机柜图

- Status: Accepted
- Date: 2026-08

## Context

机柜图可能来自 Excel、PDF、Visio、图片，也可能使用 Shape/SmartArt。

如果 V1 同时支持所有输入，Parser 和测试范围会失控。

## Decision

V1 仅承诺：

- `.xlsx`；
- 普通单元格；
- 合并单元格；
- 常见样式和尺寸信息。

V1 明确不承诺：

- OCR；
- PDF；
- Visio；
- Excel Shape/SmartArt；
- VBA/ActiveX。

## Consequences

优点：

- 可以用 `openpyxl` 做确定性结构解析；
- 跨平台；
- 两天 Beta 目标现实；
- 易于 Golden Sample 测试。

代价：

- 某些复杂 Excel 只能降级或转换后使用；
- 后续扩展非单元格对象需要新架构评估。
