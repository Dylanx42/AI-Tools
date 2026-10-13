# 2026-10-13 新建项目、机柜与设备编辑（Core/CLI）

## 问题与结果

此前可以生成空机柜 Excel，但没有可持续编辑的新建项目入口。现在增加：

- `project create`：新建默认 A01–A18、B01–B18 两排 42U 的持久 SQLite 项目，可调整每排数量和高度。
- `project add-rack`：向指定排追加机柜，或增加紧接其后的新一排，拒绝重复柜名。
- `project add-device`：按机柜名/ID 和 U 范围添加设备，支持同名设备和多行文字。
- `project edit-device`：按稳定设备 ID 修改文字、机柜、U 位或高度，保留位置与 Mapping ID。
- `project show`：读取项目状态与 ID；现有 `export` 生成单格机柜图和可筛选设备位置表。

所有入口复用 RackCore 模型、冲突校验、SQLite 验证和标准导出。重叠、越界、歧义和无效文字
被拒绝；保存失败或检测到外部改动时，不替换已有项目。

本入口只支持未绑定 Excel 的新建项目。已有业务工作簿的新增/改名写回另行设计，设备移动
继续使用 Safe Sync。GUI 新建和编辑入口暂缓，遵循用户先推进 Core/CLI 的选择。
虚拟布局、稳定身份和保存边界见 ADR-012；完整操作说明见 `docs/development/draft-projects.md`。

## 验证（2026-10-13，Linux 云端 / Python 3.12）

- 在包含已合入主线的分析包功能上运行完整 pytest：184 passed、0 skipped，包含两个真实私有
  Sheet Golden 和私有 Profile 回归；这些私有数据未进入 commit。
- Ruff、strict mypy、Qt offscreen 冒烟通过。
- 新增 10 项编辑测试覆盖 CLI 建柜/添设备/编辑/导出再识别、跨柜移动、变高机柜和第三排、稳定
  ID、同名设备、重叠/越界拒绝、重复柜名、源 XLSX 项目拒绝编辑、保存失败及外部改动保护。
- 演示流程已生成 36 个 42U 机柜、2 个示例设备的 XLSX，以及对应只读布局分析包；文字编辑和
  跨柜移动保持原设备 ID。示例不作为新增真实布局 Golden 证据。

远端 CI 和 PR 状态以 GitHub 对应提交为准。Mac/Windows GUI、Excel/WPS 的人工验收仍未完成；
现有安装包不会自动更新。

## 剩余工作顺序

1. 既有业务 Excel 的新增设备/改名安全写回，明确备份、Mapping 与回滚策略后实现。
2. RackTool Skill：分析包 → Profile → validate/dry-run → 人工确认 → 导入/确定性写回。
3. 后续 GUI 接入：新建项目、设备编辑、分析包、Profile 预览和确认，复用 Core API。
4. 发布验收：Mac 和 Windows x86-64 GUI、Excel/WPS 打开/同步/导出/恢复；ARM 只作兼容快测。

以上工作尚未完成，当前不标记 V0.6 或 V1.0 发布门禁通过。
