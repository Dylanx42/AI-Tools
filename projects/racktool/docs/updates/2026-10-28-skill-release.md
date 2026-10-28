# 2026-10-28：交付纯改名修复的完整 Skill

## 原因与交付范围

PR #29 已于北京时间 2026-10-27 合入 `main`（`12ee818862d7ae31be5b990c1e34adb7e0723307`），
但正式 Release 和本机 Skill 仍为 `2026.10.15.2`，因此日常安装尚未取得纯改名入口一致性和
结构化拒绝信息修复。本轮将既有主线代码发布为 `2026.10.28.1`，不新增 Core 功能。

本轮更新安装版本、固定下载链接和发布说明。完整包由 GitHub Actions 的
`RackTool Skill release` 工作流从合入后的干净提交构建，使用不可变标签
`racktool-skill-v2026.10.28.1`；不覆盖旧 Release、不移动旧标签、不将本机开发构建当成安装包。

纯改名复用专用 rename 计划，适用于对话、`sync edit` 和位置表回导；仍保留作用范围内的
批注、超链接、数据验证、定义名称及位置/高度变化保护。拒绝输出保留 code、实体和位置等证据。
原始问题、19 项合成回归及保护边界见 [修复记录](2026-10-26-rename-consistency.md)。

## 发布与验收依据

本记录随发布准备 PR 入库，不能据此认定附件已生成或本机已经更新。最终状态以以下证据为准：

- 发布准备 PR 精确提交的 CI：Linux、macOS、Windows 检查、Windows 打包及 Skill 包检查。
- [正式 Release](https://github.com/Dylanx42/AI-Tools/releases/tag/racktool-skill-v2026.10.28.1)
  及标签工作流：ZIP、SHA256、安装和验收文档实际存在；bundle 记录的 source_commit 必须
  等于标签提交，source_dirty 必须为 false。
- 从 Release 下载后的本机检查：外部 SHA256、包内逐文件清单、`-S --verify`、
  `-S --bundle-info`、包内 Core/vendor 实际路径、无 PyYAML 原生扩展。
- 在仓库外使用正式包的 `verify_skill_workflows.py --runner` 跑合成工作流，并对包内 Core
  执行 PR #29 的 19 项合成回归；验证改名、拒绝证据、OOXML 保留和失败回滚。
- 下载包通过后，将旧安装移到技能扫描目录之外备份，再调用正式包安装器更新本机。
  对安装目录再次核验，并使用安装后的 runner 重跑合成工作流。

发布后的实际结果与验证摘要附在上述 Release 说明中；本机完整证据和旧安装备份留在技能目录外，
不提交生成的 XLSX、SQLite、计划、token 或运行日志。

## 升级与剩余事项

不迁移或重建已有业务 SQLite。旧版本待提交 generic edit 计划在新版被规范为 rename 时，
摘要校验会要求重新预览；保留旧计划作为记录，不编辑签名内容或绕过 token。

本轮仅使用公开合成数据，真实机柜图、Excel/WPS 打开保存、外观及打印验收继续暂缓。
独立脚本通过不代表 Codex/WorkBuddy/TRAE 自然语言和技能发现已完成人工验收。
GUI 不属于本轮；新会话恢复和各 Agent 实测按现有本地验收规范另行安排。
