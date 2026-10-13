# 2026-10-13 陌生布局分析包（Core/CLI）

## 本轮结果

单格导出的 PR #18 已在远端跨平台检查和 Windows 打包通过后 squash 合入 main；对应远端
功能分支已删除。此前的本地安装包不会自动更新，桌面/Excel/WPS 人工验收继续待完成。

新增 `racktool analysis-package input.xlsx output.zip`，复用 RackCore scanner/analyzer，导出
结构、候选、异常、核对提示、源文件 Hash 和交接说明。所有材料来自一次读取的源文件快照；
原工作簿和项目数据库不变。原 XLSX 仅通过 `--include-source` 显式附带；包内 JSON 仍可能含
业务文字及隐藏页，未自动脱敏。布局适配继续用已有 Profile validate、dry-run 和 import 命令。

用户选择同时推进陌生布局和新建项目/设备编辑，GUI 优先级较低。因此本 PR 先交付分析包
Core/CLI；新建项目编辑作为独立改动，GUI 入口和 Profile 预览/确认继续待办。
协议与边界见 ADR-011。

## 验证（2026-10-13，Linux 云端 / Python 3.12）

- 完整 pytest：174 passed、0 skipped，包括已安装的两个私有 Sheet Golden 和私有 Profile 回归。
- Ruff、strict mypy、Qt offscreen 冒烟通过。
- 新增 6 项分析包测试覆盖内容/Hash/隐藏页、原文件保护、CLI 原文件附带选项、相同快照确定性、
  已有目标拒绝覆盖、验证失败保留目标、读取期间外部改动导致的快照一致性及置信度提示独立性。
- 不把这些结果解释为新的真实 workbook 兼容证据；私有数据未提交。

## 接下来

1. 新建机柜项目、添加/编辑设备并标准导出：独立 Core/CLI 任务。
2. GUI 适配入口：分析包、Profile 预览、人工确认和导入，不嵌入 Agent Runtime。
3. RackTool Skill：只调用确定性核心，规范陌生布局适配与回归证据。
4. Mac / Windows x86-64 GUI 与 Excel/WPS 打开、移动、同步、导出和恢复的人工验收。

V0.6 仍未达到整阶段完成；V1.0 发布需要以上功能与实机验收收口。
