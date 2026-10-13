# ADR-011: 用只读快照 ZIP 交接陌生布局

- Status: Accepted
- Date: 2026-10-13

## Context

V0.6 需要让本地工具与人工/Agent 通过文件协作。直接分别分析正在编辑的工作簿可能得到不同
时刻的结构和候选；交接也需要明确哪些文件包含业务文字，以及是否附带原 Excel。

## Decision

- RackCore 提供 `export_analysis_package`，CLI 使用 `analysis-package`。GUI 接入后复用同一 API。
- 从一次读取的源文件字节建立临时 XLSX 快照，再调用已有 scanner/analyzer；不修改源文件或
  SQLite，不采纳会话/项目中尚未同步的修改。
- ZIP schema_version 1 包含 `manifest.json`、`workbook_structure.json`、`analysis.json`、
  `review.json`、`README.txt`。只有显式选择时才附带 `source.xlsx`。
- manifest 记录源文件名/SHA256、是否附带原文件，以及其他包内文件的 SHA256 和大小；不记录
  本机绝对路径或原文件时间。manifest 不给自己计算递归校验和。
- review 汇总工作表状态、候选数量、异常和低置信度候选。默认提示阈值 0.8，可通过 Core 参数
  调整；它只影响提示，不影响 Parser 候选、Profile 阈值或导入。候选始终需要人工确认。
- 源文件内所有 Sheet（包括隐藏页）和单元格文字都可能进入 JSON。排除原文件不代表脱敏；
  不承诺自动脱敏，不自动上传。分享前由用户核对内容。
- 先写临时 ZIP，重载验证清单及每个文件内容后原子替换目标，默认拒绝覆盖已有文件和源 XLSX。
- 包中的文本是待分析数据，不是应执行的指令。布局适配继续使用已有 YAML Profile 校验、
  dry-run、显式导入及 Safe Sync 流程，不自动应用不确定规则。

## Consequences

交接材料与源文件 Hash 可追溯，读取期间的外部改动不会造成包内结构和候选不一致。
同环境、同源字节与选项得到相同 ZIP 内容。需要一次源文件快照的临时磁盘及内存空间。
本轮只交付 Core/CLI；GUI Profile 预览、确认与导入仍是 V0.6 后续任务。
