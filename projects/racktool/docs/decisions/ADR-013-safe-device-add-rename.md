# ADR-013: 将设备新增和文字编辑纳入既有 Safe Sync 事务

- Status: Accepted
- Date: 2026-10-13

## Context

新建项目已有 Core/CLI 编辑，但已绑定 Excel 的项目此前只有移动写回。用户要求继续开发并
增加至少 100 种机柜图与编辑验证，新增和改名必须保留原有备份、身份验证及失败保护。

## Decision

- 扩展 `WriteAction.operation` 为 move / add / rename，默认 move，既有调用兼容。
- 新增 `plan_device_add`、`plan_device_rename`，CLI 的 `sync add-device` / `sync rename` 默认
  只输出计划，显式 `--commit` 后调用原有 `commit_write_plan`。
- 所有操作校验项目、源路径和 SHA256，提交时重新生成计划逐字段核对，拒绝过期、伪造、
  重复设备、重叠 U 位或触及相同单元格的组合动作。
- 新增默认覆盖目标机柜整个连续设备区，不猜测设备列宽或前后面。已占用 U、未知文本、空白
  合并区域、注释、超链接、数据验证和命名区域相交时拒绝，不删除未知对象。
- 新设备计划中分配独立 ID，位置和 Mapping ID 与其关联；写后以预期映射重扫，验证新 ID
  已续上。改名只修改原锚点文字，保持 device / placement / mapping ID、U 范围、合并与样式。
- 新增/改名文字必须非空、最多 32767 字符，绑定 Profile 忽略的文字被拒绝；新文字按字面量
  保存，以 `=` 开头也不是公式。移动则保留原单元格数据类型，避免文字变公式或公式变文字。
- 新建项目和 Safe Sync 共用 Core 文字校验，拒绝非法 XML 控制字符与无效 Unicode；不先把
  无法导出的文字存进 SQLite，也不靠 trim 掩盖非法柜名。合法换行、TAB、Unicode 和符号保留。
- 越界 U 位在遍历范围之前拒绝，避免巨大的错误输入导致长时间枚举。
- 复用原有 workbook + SQLite 备份、临时文件、重载/重扫验证、原子提交和 SQLite 失败后的
  工作簿/数据库回滚；原文件存在外部变化时拒绝覆盖。保持现有单用户事务边界，不承诺多人隔离。
- 新建未绑定项目仍使用 ADR-012 的编辑入口，不清空绑定、不直接改 SQLite 模拟 Excel 写回。

## Consequences

确定性新增/改名无需 Office 或 Agent。GUI 接入后只能调用相同计划与提交 API。
本 ADR 在 2026-10-13 的增量范围不包含已有设备调整 U 高度、跨 Sheet 移动或 Excel Shape。
前两项已由后续 [ADR-016](ADR-016-skill-workflows-and-table-roundtrip.md) 扩展：同一项目绑定的
同一工作簿内可跨 Sheet 移动，move 保持高度、edit 可显式改高；原有 Safe Sync 保护继续生效。
Excel Shape 解析编辑仍不支持。本 ADR 的新增/改名事务设计继续有效。
生成布局矩阵与真实私有工作簿回归分别记录，不以 synthetic 结果宣称任意 Excel 兼容或实机通过。
