# Version Gates

本目录记录 RackTool 每个阶段的实现、验证、Golden Sample、回归结果和门禁决定。

各阶段报告保留原阶段证据；当前整合状态以
[V0.5 Integrated Audit](V0.5-integrated-audit.md) 为准。只有报告明确给出适用范围内的 PASS，
才允许据此继续下一阶段；automated PASS 不得替代 manual validation。
私有工作簿只使用不泄露业务内容的代号和统计结果；原始数据、实际分析 JSON 和待确认清单保留在
Git 忽略的 `samples/private/`。

当前状态：

- Phase 0：PASS；V0.1 Reader、V0.2 Profile、V0.3 Identity & Mapping：**AUTOMATED PASS**。
- V0.4 Safe Sync：**AUTOMATED PASS**；Microsoft Excel/WPS 实机打开及写回仍为
  **MANUAL VALIDATION PENDING**。
- V0.5 Local GUI：**AUTOMATED PASS — RackCore + GuiSession/headless**；macOS/Windows GUI
  人工检查仍为 **MANUAL VALIDATION PENDING**。
- 当前审计环境未安装 PySide6，Qt widget window 未运行。
