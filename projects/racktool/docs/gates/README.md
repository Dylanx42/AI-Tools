# Version Gates

本目录记录 RackTool 每个阶段的实现、验证、Golden Sample、回归结果和门禁决定。

各阶段报告保留原阶段证据；V0.1～V0.5 的历史整合审计见
[V0.5 Integrated Audit](V0.5-integrated-audit.md)。当前入口与能力范围以[项目 README](../../README.md)
及后续 ADR/更新记录为准。只有报告明确给出适用范围内的 PASS，
才允许据此继续下一阶段；automated PASS 不得替代 manual validation。
私有工作簿只使用不泄露业务内容的代号和统计结果；原始数据、实际分析 JSON 和待确认清单保留在
Git 忽略的 `samples/private/`。

2026-10-30：正式 Skill 在本机 Codex 的实际调用和独立新会话恢复合成验收通过，见
[本次记录](../updates/2026-10-30-agent-recovery-acceptance.md)。真实图、Windows 实机和 Excel/WPS
继续暂缓；自动化、合成验收和各平台人工验收分别记录。

以下为 V0.1～V0.5 历史阶段状态：

- Phase 0：PASS；V0.1 Reader、V0.2 Profile、V0.3 Identity & Mapping：**AUTOMATED PASS**。
- V0.4 Safe Sync：**AUTOMATED PASS**；Microsoft Excel/WPS 实机打开及写回仍为
  **MANUAL VALIDATION PENDING**。
- V0.5 Local GUI：早期表格式窗口在 macOS 人工检查中因可用性不达标被拒绝；已按批准的
  机柜可视化、设备详情、移动抽屉、待同步队列和全局安全同步工作流完成重构。
- 重构后的 V0.5 为 **AUTOMATED PASS — RackCore + GuiSession + PySide6 headless**；完整套件
  120 passed，真实私有工作簿副本完成 90 racks / 710 devices 运行时加载和有界渲染检查。
- 新版 macOS GUI 已启动等待用户验收，Windows GUI 仍待检查；两项均为
  **MANUAL VALIDATION PENDING**，不得由 headless 或启动成功替代。
