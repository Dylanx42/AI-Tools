# ADR-012: 先支持未绑定 Excel 的新建项目编辑

- Status: Accepted
- Date: 2026-10-13

## Context

用户希望同时推进陌生布局适配与新建机柜/设备编辑，GUI 优先级暂低。已有 Safe Sync 负责
已导入 XLSX 的设备移动；新增设备和修改文字直接套进移动事务会绕过原有身份及来源校验。

## Decision

- RackCore 提供新建项目、追加机柜、添加设备、修改设备文字/位置的 API，CLI 仅调用这些 API。
- 新建项目保存为 SQLite，`source_workbook=None`、`profile_id=None`，metadata 使用
  `project_mode=draft`、`draft_schema_version=1`。只有这种项目可以通过本编辑入口修改。
- 初始 A/B 两排复用空模板几何，但项目、机柜、设备、位置、Mapping 使用独立 ID。同名设备
  可存在，身份不来自文字；修改设备时保留 device_id / placement_id / mapping_id。
- U 位范围、有效机柜、重复柜名与唯一目标先校验，保存前再复用 `project_error_conflicts`，
  拒绝重叠、越界、Mapping 不一致等错误。
- Rack/SourceMapping 中的行列是虚拟布局坐标，服务于标准导出排序与项目校验，不代表某个已有
  XLSX 的真实来源。虚拟 fingerprint 是项目身份种子，不冒充源文件 SHA256。
- SQLite 是此模式的主数据。先保存临时数据库并重载校验，再检查原项目文件的 SHA256 是否
  在编辑期间改变，最后原子替换目标；失败不替换，外部改动被保留。新建默认拒绝覆盖已有文件。
  这是离线单用户编辑流程，不提供多人协作或跨进程事务隔离的承诺。
- XLSX 由现有标准导出生成，含单格机柜图和设备位置表。导出不绑定源文件，也不重建当前 ID。
- 已绑定 Excel 的项目在此入口被拒绝，继续使用 Safe Sync；新增/改名写回由后续
  ADR-013 的独立计划实现。不得靠清空 source_workbook 绕过这一边界。

## Consequences

新项目可在 Core/CLI 中完成“建柜 → 添加/编辑设备 → 冲突检查 → 导出”，不要求安装 Office
或 Agent。应保留原 SQLite；重新导入导出 XLSX 是创建另一个项目，不保证续用草稿 ID。
GUI 当前不载入这种未绑定的项目，新建/设备编辑界面后续复用本 API。持久化 schema 不变，
既有导入、Profile、重扫和 Safe Sync 行为不变。
