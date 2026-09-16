# ADR-010: GUI 项目状态和备份使用受管本地存储

- Status: Accepted
- Date: 2026-09

## Context

GUI 旧实现把 `workbook.xlsx.sqlite` 及每次事务产生的 `.sqlite.bak-*` 直接放在源 Excel
旁边。频繁重扫或同步会在用户目录堆积实现细节文件，既影响日常使用，也让真正用于恢复 Excel
的备份难以辨认。

ADR-008 仍要求真实 XLSX 写回前必须存在可恢复备份；ADR-009 仍要求持久保存 SQLite 项目状态。
本决策只改变这些文件的默认存放和保留策略，不降低写回安全标准。

## Decision

- GUI 默认把 SQLite 项目状态放入操作系统的 RackTool 应用数据目录，不再创建 Excel 同目录
  sidecar。CLI 明确传入的 SQLite 路径保持不变。
- macOS 使用 `~/Library/Application Support/RackTool`；Windows 使用 `%LOCALAPPDATA%/RackTool`；
  Linux 使用 `$XDG_DATA_HOME/RackTool` 或 `~/.local/share/RackTool`。
- 每个源工作簿使用“可读文件名 + 规范化绝对路径 Hash”的独立目录，避免同名文件互相覆盖。
- XLSX Safe Sync 恢复备份也存入该受管目录；每个工作簿最多保留最新 3 份，且最长 30 天。
- SQLite 事务备份不作为长期用户版本：成功、拒绝或成功回滚后立即删除；进程异常中断留下的
  事务备份最多保留 7 天。
- 清理在应用启动、打开工作簿/项目以及创建新恢复备份时机会式执行，不安装后台服务或定时任务。
- 下次打开工作簿时，RackCore 校验并迁移旧版 `.xlsx.sqlite` 和精确匹配的备份文件；内容冲突时
  停止自动迁移，不覆盖任一份数据。
- 源文件同目录临时 XLSX 只用于同文件系统原子替换，并在成功或失败时立即清除。
- 测试可用 `RACKTOOL_DATA_DIR` 把受管目录隔离到临时路径。

## Consequences

优点：

- 用户的 Excel 目录只保留业务文件和用户主动导出的文件；
- 必要恢复能力不变，重复事务快照不会无限增长；
- 路径隔离、迁移和保留规则可跨平台自动测试。

代价：

- GUI 项目文件不再默认与 Excel 并排可见；
- 工作簿路径发生变化时需要迁移或重新绑定项目状态；
- 受管目录仍需纳入整机备份策略。
