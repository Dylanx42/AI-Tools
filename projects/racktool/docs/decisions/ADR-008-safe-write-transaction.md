# ADR-008: XLSX 写回必须采用事务式安全流程

- Status: Accepted
- Date: 2026-08

## Context

真实机柜图可能是生产项目文档。比“解析错误”更严重的是写回破坏原文件。

## Decision

任何写回必须遵循：

```text
Validate intent
  ↓
Conflict check
  ↓
Backup source
  ↓
Write temporary file
  ↓
Reload temporary file
  ↓
Validate workbook + mapping
  ├─ PASS → Commit target
  └─ FAIL → Abort / Rollback
```

默认禁止：

- 直接覆盖且无备份；
- 冲突时强制写入；
- Validation 未通过仍替换正式文件。

## Consequences

优点：

- 用户敢在真实项目文件上使用；
- 自动化测试可覆盖失败路径；
- 错误可恢复。

代价：

- 实现复杂度和 I/O 增加；
- 需要临时文件、备份策略和错误报告。
