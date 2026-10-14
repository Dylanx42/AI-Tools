# 2026-10-15：修正 Skill 分发与普通安装

本机 Agent 按上一版提示词，在没有 GitHub Release 时临时下载源码并构建；该行为来自
维护者提供的回退流程，并非 Agent 自作主张。现将开发者构建与普通安装分开。

新增 RackTool 专用版本标签触发的 GitHub Release 工作流，构建和校验在 GitHub runner 完成，
PR 阶段不会发布；发布作业仅在专用标签上下文申请仓库 contents:write。
附件为含 Core/CLI/Profile/纯 Python 依赖/许可证的 ZIP、SHA256、安装和验收 MD。
普通安装文档与提示词改为直接下载完整发布附件；下载/导入失败如实报告，不默认构建源码。
不修改 Core 行为或业务数据，不改变 Python 3.11+ 要求与 Agent 本机兼容性待验收状态。

验证包括工作流解析、构建/发布权限与标签边界、GitHub 上的隔离包 smoke 检查，以及发布后
从实际下载链接取回 ZIP，对照 SHA256、源码提交、完整性和脱离仓库运行结果。
只有 Release 和附件实际存在才报告正式下载链接可用。
