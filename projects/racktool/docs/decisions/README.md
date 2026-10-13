# Architecture Decision Records

当前已接受 ADR：

1. `ADR-001-rackcore-source-of-truth.md` — RackCore 是唯一核心能力层
2. `ADR-002-no-agent-in-gui.md` — GUI 不嵌入 Agent Runtime
3. `ADR-003-xlsx-cells-only-v1.md` — V1 聚焦 XLSX 单元格/合并单元格
4. `ADR-004-profile-first-extensibility.md` — Profile 优先扩展陌生布局
5. `ADR-005-cross-platform-no-office-com.md` — 不依赖 Office COM
6. `ADR-006-monorepo-boundary.md` — AI-Tools monorepo 项目边界
7. `ADR-007-open-source-offline-first.md` — 开源/内部共享、Offline-first
8. `ADR-008-safe-write-transaction.md` — XLSX 安全事务式写回
9. `ADR-009-sqlite-project-state.md` — SQLite 保存本地项目身份与 Mapping
10. `ADR-010-managed-local-storage.md` — GUI 项目状态与备份使用受管本地存储和有界保留
11. `ADR-011-analysis-package.md` — 从只读快照生成可追溯的陌生布局分析包
12. `ADR-012-draft-project-editing.md` — 未绑定 Excel 的新建项目编辑与稳定身份
13. `ADR-013-safe-device-add-rename.md` — 已绑定 Excel 的设备新增/文字编辑使用 Safe Sync 事务
14. `ADR-014-skill-room-export.md` — Skill 主入口、机房分 Sheet、U 方向与原版面导出

架构方向发生变化时，应新增 ADR 或明确 supersede 旧 ADR。
