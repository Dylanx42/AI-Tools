# RackTool 架构总览

## 1. 架构目标

RackTool 的架构必须同时满足：

- 本地可独立运行；
- Windows/macOS 跨平台；
- Excel 读写确定性、可测试；
- 可识别多种机柜图布局；
- 支持 GUI、CLI、Skill 多入口；
- Agent 不是运行前置条件；
- 一套核心逻辑，避免功能分叉。

## 2. 总体架构

```text
                         ┌─────────────────┐
                         │  RackTool Skill │
                         │ Agent 智能辅助   │
                         └────────┬────────┘
                                  │
                         Profile / JSON
                                  │
┌─────────────────┐      ┌────────▼────────┐
│ RackTool Local  │─────▶│     RackCore     │◀──── CLI
│ GUI / 驾驶舱     │      │ Python 核心引擎  │
└─────────────────┘      └────────┬────────┘
                                  │
                   ┌──────────────┼──────────────┐
                   ▼              ▼              ▼
              XLSX Adapter     SQLite        Profile Store
              openpyxl         Mapping       YAML
```

### 核心原则

> GUI、CLI、Skill 都是入口；RackCore 才是产品能力。

## 3. 建议模块边界

```text
src/racktool/
├── models/
│   ├── rack.py
│   ├── device.py
│   ├── mapping.py
│   └── analysis.py
│
├── core/
│   ├── workbook.py
│   ├── detector.py
│   ├── extractor.py
│   ├── mapper.py
│   ├── validator.py
│   ├── sync.py
│   └── backup.py
│
├── profiles/
│   ├── loader.py
│   ├── matcher.py
│   └── validator.py
│
├── persistence/
│   └── sqlite.py
│
├── cli/
│   └── main.py
│
└── gui/
    └── ...
```

这是目标边界，不要求第一天生成所有文件。

## 4. 数据流

### 4.1 导入/分析

```text
XLSX
 ↓
Workbook Scanner
 ↓
Workbook Structure
 ↓
Rack/U Candidate Detector
 ↓
Profile Matcher（如果有）
 ↓
Device Extractor
 ↓
Validator
 ↓
Structured Rack Project
```

### 4.2 写回

```text
Structured Change
 ↓
Conflict Validator
 ↓
Write Plan
 ↓
Backup
 ↓
Temporary XLSX
 ↓
Apply Changes
 ↓
Reload + Validate
 ↓
Commit / Rollback
```

### 4.3 未知格式

```text
XLSX
 ↓
低置信度
 ↓
Analysis Package
 ↓
人工 / Agent Skill
 ↓
Profile YAML
 ↓
RackCore Validate
 ↓
保存 Profile
 ↓
重新解析
```

## 5. 为什么 RackCore 不依赖 Agent

日常任务例如：

- 设备从 A01 31–32U 移到 A03 20–21U；
- 检查目标是否空闲；
- 更新 Mapping；
- 写回 Excel；

都是确定性操作，不应使用概率模型。

Agent 的价值集中在：

- 看懂陌生布局；
- 生成 Profile；
- 分析异常；
- 辅助调试。

## 6. 为什么不用 Excel COM

目标是让同一 RackCore 在 macOS / Windows 上运行。

采用 `openpyxl` 直接处理 OOXML/XLSX 可避免：

- Office 安装依赖；
- COM 只在 Windows 可用；
- Excel 进程管理；
- GUI 阻塞；
- 跨平台测试困难。

代价是：对 Shape、ActiveX、宏等复杂对象支持有限，因此这些不进入 V1 承诺范围。

## 7. 主数据与视图

推荐事实层：

```text
Rack Project
├── Racks
├── Devices
├── Placements
├── Source Mappings
└── Profiles
```

Excel：

- 是外部输入；
- 是可视化输出；
- 可保留原样式；
- 但不是唯一身份来源。

## 8. GUI 定位

GUI 是“驾驶舱”，即人的可视化操作界面。

第一阶段 GUI 重点：

- 设备清单；
- 机柜视图；
- 异常项；
- Mapping；
- 修改位置；
- 冲突提示；
- 同步；
- 备份恢复。

GUI 不承担核心 Parser 逻辑。

## 9. Skill 定位

Skill 是最轻量的 Agent 分享方式之一，但兼容性依赖 Agent 是否支持相同 Skill 机制和脚本执行能力。

RackTool Skill 应：

- 引导 Agent 阅读项目规则；
- 调用 CLI；
- 读取 Analysis Package；
- 生成 Profile；
- 不直接绕过 RackCore 写 XLSX。

## 10. 持久化

SQLite 主要用于：

- 稳定 ID；
- Project 状态；
- Device/Rack Mapping；
- 操作历史/元数据（视实现而定）。

原则：

- SQLite 不是必须贯穿所有 Parser 单测；
- 核心模型应可独立序列化为 JSON；
- 不使用服务器数据库作为 V1 前置条件。

## 11. 可演进边界

V1 之后可能扩展：

- Shape 解析；
- Visio；
- OCR；
- NetBox/CMDB；
- Web 视图；
- 多人协作。

这些都必须通过新 ADR 决定，不提前污染 V1 核心。
