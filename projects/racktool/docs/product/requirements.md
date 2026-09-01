# RackTool 产品需求说明（Requirements）

## 1. 项目定位

RackTool 是一个**开源、跨平台、离线优先**的 Excel 机柜管理工具，用于解决“设备清单”和“机柜图”长期双份维护的问题。

核心目标不是做商业 SaaS，而是：

- 自己可长期使用；
- 公司同事可直接使用或二次开发；
- 支持 Windows / macOS；
- 支持本地 APP、CLI、Agent Skill 三种入口；
- 所有入口共用同一个 RackCore。

## 2. 原始问题

当前机柜规划通常存在两套信息：

1. 设备清单：设备名称、型号、IP、机柜、U 位等；
2. Excel 机柜图：通过单元格、合并单元格、颜色等表达设备占用位置。

它们需要人工重复维护，容易出现：

- 机柜图更新了，设备清单位置没改；
- 清单更新了，机柜图没移动；
- 设备可能占 1U、2U、5U、6U 等不同高度；
- 老项目/外部项目的机柜图排版不统一；
- 新项目希望快速复用旧数据，而不是重新录入。

## 3. 产品目标

### 3.1 核心目标

RackTool 应建立统一的结构化事实层，至少表达：

- 设备/对象内容；
- 所属机柜；
- 起始 U；
- 结束 U；
- 占用 U 数；
- 来源 Sheet / Range；
- 稳定设备 ID；
- 映射状态和置信度。

### 3.2 双向工作流

#### 方向 A：机柜图 → 设备清单

从 `.xlsx` 读取：

- 机柜名称；
- U 标尺；
- 合并单元格；
- 单元格文本；
- 占用 U 数；

生成结构化设备清单。

#### 方向 B：设备清单 → 机柜图

修改结构化数据中的：

- 机柜；
- Start U / End U；
- 设备显示文本（在允许范围内）；

由 RackCore 安全写回 Excel。

### 3.3 陌生机柜图

V1 不追求“任何 Excel 100% 自动识别”。目标是：

- 对基于单元格/合并单元格绘制的 XLSX 做自动识别；
- 自动识别失败时进入半自动流程；
- 支持 Profile 描述布局；
- 一次适配后可复用同类格式；
- Agent Skill 可协助生成 Profile；
- 低置信度必须允许人工确认。

## 4. 用户类型与入口

### 4.1 普通使用者

使用本地 RackTool GUI：

- 导入 Excel；
- 查看机柜；
- 查看设备清单；
- 修改 U 位；
- 检查冲突；
- 同步 Excel；
- 导出清单；
- 恢复备份。

### 4.2 高级/自动化使用者

使用 CLI：

```text
racktool analyze <file.xlsx>
racktool validate <file.xlsx>
racktool export <file.xlsx>
racktool profile ...
```

CLI 具体参数在实现阶段稳定后确定。

### 4.3 Agent 使用者

安装 RackTool Skill：

- 上传陌生 XLSX；
- 让 Agent 理解结构；
- 调用 RackCore/CLI；
- 生成 Profile；
- 输出异常解释或规则建议。

Skill 不复制一套 Parser。

## 5. V1 功能需求

### FR-001 XLSX 工作簿扫描

系统能够读取 `.xlsx` 的：

- Sheet；
- 单元格值；
- 合并单元格；
- 行高/列宽；
- 常用样式信息；
- 行列坐标。

### FR-002 机柜候选识别

系统应能基于以下线索形成机柜候选：

- 连续或近连续 U 编号；
- 42U / 47U / 48U / 53U 等高度；
- 左右重复 U 轴；
- 机柜标题/名称；
- 中间设备区域。

不得把某一个固定高度写死为唯一格式。

### FR-003 设备对象提取

系统应将单元格/合并单元格映射为设备对象候选，并计算：

- rack；
- start_u；
- end_u；
- height_u；
- source_sheet；
- source_range；
- display_text；
- confidence。

### FR-004 标准数据导出

至少支持导出：

- JSON；
- Excel 清单（后续实现）；
- 便于测试的稳定序列化格式。

### FR-005 Profile

支持 YAML Profile 描述未知布局，至少覆盖：

- 机柜标题位置/规则；
- U 轴位置；
- U 方向；
- 设备区域；
- 忽略文本；
- 可选的文本解析提示。

### FR-006 稳定身份与 Mapping

- Rack 有稳定 `rack_id`；
- Device 有稳定 `device_id`；
- 不能仅用设备显示文本作为唯一身份；
- 维护 `Device ↔ Rack/U ↔ Sheet/Range` 映射。

### FR-007 冲突检测

写回前必须检查：

- U 越界；
- 目标 U 被占用；
- 合并单元格冲突；
- 设备高度与目标范围不一致；
- Mapping 歧义。

### FR-008 安全写回

支持从结构化数据写回 XLSX，并尽可能保留：

- 原有样式；
- 合并关系；
- 机柜图布局；
- 与目标设备无关的数据。

任何写回必须支持备份和验证。

### FR-009 GUI

V1 GUI 至少包含：

- 打开项目/Excel；
- 设备清单视图；
- 机柜视图；
- 异常/低置信度视图；
- Mapping 信息；
- 修改设备机柜/U 位；
- 冲突提示；
- 同步/导出；
- 备份/恢复入口。

拖拽可以在基础 GUI 稳定后加入，不是首个 GUI 版本的硬门槛。

### FR-010 Analysis Package

本地 APP 在无法确定布局时，可导出分析包供 Agent/人工分析，建议包含：

- workbook structure；
- merged ranges；
- candidate U axes；
- candidate rack regions；
- source workbook 或脱敏副本；
- 基础统计信息。

Agent 输出 Profile，再由本地 APP 导入验证。

### FR-011 Skill

仓库中提供 RackTool Skill：

- 说明 Agent 如何调用 CLI/RackCore；
- 如何判断未知布局；
- 如何生成 Profile；
- 如何处理低置信度；
- 不直接绕过 RackCore 修改 XLSX。

## 6. 非功能需求

### NFR-001 跨平台

- macOS Apple Silicon；
- Windows 10/11 x86-64；
- Windows 11 ARM 尽可能兼容。

### NFR-002 离线优先

普通使用不要求联网，不要求 Agent，不要求云服务。

### NFR-003 低依赖

不要求：

- Docker；
- MySQL/PostgreSQL；
- Excel/WPS 安装才能解析；
- 后台常驻服务。

### NFR-004 可测试

关键 Parser、Mapping、Sync 都必须支持自动化测试。

### NFR-005 数据安全

真实项目文件默认不原地覆盖；失败可恢复。

### NFR-006 可扩展

新增一种机柜图格式，优先通过 Profile / fixture / 规则扩展，而不是硬编码客户特例。

### NFR-007 可分享

仓库、Skill、本地 Release 都可以独立分发。

## 7. V1 明确不做

以下内容推迟到 V1 以后评估：

- PDF/图片 OCR；
- Visio 解析；
- Excel Shape / SmartArt；
- VBA / ActiveX；
- Web 多人协作；
- 云账户；
- SaaS；
- CMDB/NetBox/SNMP 自动发现；
- 商业授权、计费、多租户；
- GUI 内嵌 Codex/Agent Runtime；
- 任意陌生 Excel 100% 无标记原样双向同步的承诺。

## 8. V1 验收标准

V1.0 发布前至少满足：

1. 两类以上真实、不同布局的机柜 XLSX 可以稳定解析；
2. Golden Samples 回归测试长期通过；
3. 标准数据能表达机柜、U 位、设备、高度、来源位置；
4. 双向同步可用；
5. 冲突检测有效；
6. 写回具备备份、Validate、失败保护；
7. Windows x86-64 + Office/WPS 实机验收；
8. macOS Apple Silicon 实机验收；
9. CLI 可用；
10. 本地 GUI 可用；
11. Skill 可独立分享；
12. 不依赖 Agent 也能完成日常工作流。

## 9. 当前 Golden 证据与后续补充规则

- 当前已有一个真实私有机柜 workbook，其中两类实质不同的 Sheet 布局已完成人工确认、
  Sheet-scoped expected JSON、源文件 Hash 和持久 acceptance。
- 资产清单 workbook 只作为独立对账参考，不是第二个机柜布局 Golden Sample。
- 私有源文件、expected、分析结果和 acceptance 保留在 Git 忽略的 `samples/private/`；不得把
  敏感业务内容提交到仓库。
- Synthetic fixture 用于证明通用行为，不能冒充真实 Golden 或真实格式兼容性证据。
- 新增真实布局时仍需提供脱敏或私有保存的原始 `.xlsx`、人工正确答案，以及颜色、备注、预留位
  等语义的期望行为。
