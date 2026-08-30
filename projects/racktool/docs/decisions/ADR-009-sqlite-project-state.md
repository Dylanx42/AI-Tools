# ADR-009: 使用 SQLite 保存本地项目身份与 Mapping

- Status: Accepted
- Date: 2026-08

## Context

V0.3 需要稳定 `rack_id` / `device_id` 和 SourceMapping。这些身份不能每次从
`display_text` 或 Excel 坐标重新生成，否则改名、移动、重扫都会复制对象。

## Decision

- 每个 RackTool 项目使用一个本地 SQLite 文件保存项目状态。
- SQLite 只存身份、Placement、SourceMapping 和必要的机柜几何信息。
- Parser / Profile 继续保持无数据库依赖；核心模型仍可序列化为 JSON。
- 不引入服务器数据库，不把 SQLite 当作 Excel 的替代事实层。

## Consequences

优点：

- 重扫可以按 Mapping 续上身份；
- 测试可用临时 SQLite 文件覆盖；
- 离线、低依赖。

代价：

- 需要明确 `import` 与 `rescan` 的命令边界；
- 项目状态文件必须和源工作簿一起纳入备份策略。
