# RackTool 背景调研与方案形成记录

## 1. 调研起点

项目源于一个实际 IDC 机柜规划维护问题：

- 已有 Excel 设备清单；
- 已有 Excel 机柜图；
- 两者由人工独立维护；
- 设备位置变更时需要重复修改；
- 设备占用 U 数不固定，可为 1U、2U、5U、6U 等；
- 机柜图常通过“合并单元格”表达占用范围。

讨论中使用了两种明显不同排版风格的机柜图截图作为例子：

- 一种较规则，多机柜横向排列，U 位序列清晰；
- 一种旧项目/外部风格，左右可能重复 U 标尺、设备区域和文本排版更复杂。

这促成了核心问题：**能否让设备清单和机柜图不再是两套数据，而是同一份结构化数据的两个视图？**

## 2. 真正要解决的问题

经过讨论，问题被重述为三层：

### 2.1 数据模型

把机柜图背后的事实抽象为：

```text
设备/对象 → 机柜 → Start U → End U → Height U
```

Excel 只是表达方式，不应成为唯一事实来源。

### 2.2 双向编辑

希望支持：

```text
机柜图更新 → 设备清单位置同步
设备清单更新 → 机柜图位置同步
```

### 2.3 陌生机柜图导入

理想状态：

```text
陌生 XLSX → 自动/半自动识别 → 标准结构化数据
```

后续再决定是否保留原始机柜图样式继续双向维护。

## 3. “固定模板”与“任意陌生格式”的双向钢人论证

### 3.1 支持固定模板/标准化方案的最强理由

- 格式可预测；
- 双向写回简单；
- 样式和合并规则容易维护；
- 稳定性最高；
- 跨平台依赖少；
- 更容易做自动测试。

如果陌生文件只作为导入源：

```text
陌生 Excel → 标准数据 → RackTool 标准机柜图
```

工程难度明显更低。

### 3.2 支持陌生 XLSX 直接识别的最强理由

Excel `.xlsx` 本身是结构化文件，不是图片。程序可以直接读取：

- 单元格坐标；
- 合并区域；
- 文字；
- 边框；
- 颜色；
- 行高；
- 列宽；
- Sheet。

多数人工机柜图虽样式不同，但通常保留强结构特征：

- 连续 U 数字；
- 机柜名称；
- 设备文本区域；
- 合并单元格跨越若干 U。

因此，对“基于单元格/合并单元格绘制的 XLSX”做半自动/高自动识别具有现实可行性。

### 3.3 反对“任意陌生 Excel 永久原样双向同步”的最强理由

Excel 并没有“机柜”“设备”的语义。

程序只能看到：

- 某个 range 被合并；
- 某个 cell 有文字；
- 某列有 47、46、45……

但无法天然知道：

- 哪一列是 U 号；
- 左右两个 U 号是否属于同一机柜；
- 某颜色代表设备还是预留；
- 多行文本里哪个字段是设备名；
- 移动后应继承什么样式；
- 某个奇怪合并是设备还是排版。

“读”陌生格式与“安全写回原陌生格式”不是同一个难度级别。

## 4. 最终选择：受控的第二种方案（方案 2A）

难度评估形成了三个等级：

| 方案 | 难度 | 结论 |
|---|---:|---|
| 陌生图导入后转标准格式，再双向同步 | 约 4/10 | 稳妥基础 |
| 陌生图识别后建立 Mapping/Profile，并保留原样式继续同步 | 约 6–7/10 | 值得做，最终采用 |
| 任意陌生 Excel、无标记、无约束、100% 原样永久双向 | 约 9/10 | V1 不做 |

最终设计：

1. 第一次解析陌生 XLSX；
2. 建立 Rack Mapping；
3. 建立 Device Mapping；
4. 必要时保存隐藏元数据或外部状态；
5. 保存布局 Profile；
6. 以后按 Mapping/Profile 确定性处理，而不是每次让 AI 重新猜。

## 5. 关键洞察：Profile

陌生格式第一次识别后保存规则，例如：

```yaml
profile: legacy_layout_01

rack:
  name_range: F3:I3

u_axis:
  left: F
  right: I
  direction: descending

device_area:
  start_column: G
  end_column: H
```

这样：

- 第一次需要理解；
- 后续同类文件直接复用；
- Profile 可以提交到 Git；
- 同事适配一次，公司所有人都能受益。

## 6. Python、Skill 与本地 APP 的关系

讨论一度考虑“本地 APP 内嵌 Agent/Codex App Server”，最终明确放弃作为默认路线。

最终结构：

```text
                   RackCore
                      │
          ┌───────────┴───────────┐
          │                       │
      RackTool APP           RackTool Skill
       本地 GUI                Agent 入口
          │                       │
          └──── Profile/JSON ─────┘
```

### 6.1 RackCore

Python 核心，负责：

- XLSX 扫描；
- 机柜/U 识别；
- 设备提取；
- Mapping；
- 冲突检查；
- 写回；
- 备份；
- Validate；
- Rollback；
- Profile 解析。

### 6.2 本地 APP

本地 GUI 被称为“驾驶舱”，含义只是：**人实际操作 RackTool 的可视化界面**。

它不是 Agent 壳，不需要把 Codex 套在里面。

主要适合：

- 看机柜；
- 看清单；
- 改 U 位；
- 冲突检查；
- 同步 Excel；
- 导入/导出 Profile；
- 恢复备份。

### 6.3 Skill

Skill 是轻量分享和智能辅助入口：

- Agent 读 SKILL.md；
- 调用同一套 RackCore/CLI；
- 分析陌生布局；
- 生成 Profile；
- 解释异常。

Skill 不应重新实现一套 Excel Parser。

## 7. 为什么不把 Agent 嵌进 GUI

最终结论：没有必要。

原因：

- 用户本来就可以直接用 Codex/Agent + Skill；
- GUI 日常操作大多是确定性任务，不需要 AI；
- 嵌入 Agent 增加认证、运行时、网络、故障面和分发复杂度；
- 项目不是商业软件，不需要隐藏 Agent 的存在；
- 公司同事可以选择“本地 APP”或“Skill”，无需强绑。

因此 V1 明确采用：

> **要么本地软件，要么 Skill；两者通过文件协议协调，但互不嵌套。**

## 8. 本地 APP 与 Skill 的协调方式

当本地 APP 遇到未知格式：

```text
unknown.xlsx
   ↓
RackTool 分析
   ↓
低置信度
   ↓
导出 Analysis Package
```

可能包含：

```text
workbook_structure.json
merged_cells.json
candidate_racks.json
source.xlsx
```

用户把分析包交给 Agent + RackTool Skill：

```text
Agent → profile_customer_a.yaml
```

再导回 RackTool：

```text
导入 Profile → RackCore Validate → 重新解析
```

无需 APP 与 Agent 互相联网调用。

## 9. 技术栈讨论结果

初步推荐：

- Python：核心语言；
- `openpyxl`：XLSX 结构读写；
- SQLite：本地状态/Mapping；
- PySide6：跨平台 GUI；
- pytest：测试；
- YAML：Profile；
- GitHub：代码与版本管理；
- Codex Cloud：主要开发执行环境。

原则：

- 不依赖 Windows COM；
- 不要求 Excel/WPS 进程；
- 不依赖 Docker；
- 不依赖服务器数据库；
- Windows/macOS 共用同一核心。

## 10. 安全写回原则

讨论中明确：真正危险的不是“读错”，而是“写坏真实项目文件”。

因此所有写回必须采用事务式思路：

```text
源文件
  ↓
Backup
  ↓
临时文件写入
  ↓
重新加载
  ↓
Validate
  ├─ PASS → 替换正式目标
  └─ FAIL → 保留原文件 + 报错/回滚
```

并在写入前检查：

- U 位越界；
- 设备重叠；
- 合并冲突；
- 目标高度；
- Mapping 歧义。

## 11. 项目定位从“工具”到“开源工程”

用户明确：

- 不做商业软件；
- 希望开源或至少公司内部共享源码；
- 同事可以直接用；
- Skill 也可独立分发；
- 同一 Git 仓库维护本地 APP 与 Skill；
- 不维护两套核心代码。

可选开源许可证后续评估 MIT / Apache-2.0；早期也可以先放私有 GitHub/GitLab。

## 12. 开发环境讨论

现有设备：

- MacBook Air：主日常设备；
- Parallels Desktop Windows 11 ARM VM；
- Lenovo R7000P 2021 / RTX 3060，x86-64 Windows 笔记本。

最终分工：

| 环境 | 作用 |
|---|---|
| Codex Cloud | 主开发执行环境 |
| GitHub `AI-Tools/projects/racktool` | 唯一代码事实来源 |
| MacBook Air | macOS 实机验收、必要时本地开发 |
| PD Win11 ARM | 快速 Windows 兼容性检查 |
| R7000P x86-64 | Windows/Office/WPS 正式人工验收 |
| GitHub Actions（后续） | 自动测试、打包、Release |

## 13. GitHub / Codex Cloud 工作方式

项目计划：

```text
AI-Tools/
└── projects/
    └── racktool/
```

- `AI-Tools` 是远端 monorepo；
- RackTool 是其中一个项目目录；
- 不建立嵌套仓库；
- Codex Cloud 每次任务只允许在 `/projects/racktool` 范围内工作；
- 项目级 `AGENTS.md` 约束 Codex；
- 设计文档放 `docs/`，AGENTS 只作为地图和规则入口。

## 14. 开发周期讨论

最初粗估完整 V1.0：约 60–90 个有效工程工时；在 Codex 主力开发、用户集中投入和技术审计配合下，进一步收敛为：

- 连续 2 个完整工作日：目标为“实际可用 Beta”；
- 3–5 个完整工作日：更接近成熟 V1.0；
- 前两天不追求 GUI 美化，优先 RackCore / Mapping / Sync / Tests。

两日冲刺理想结果：

### Day 1

- Phase 0；
- 数据模型；
- 项目骨架；
- Workbook Scanner；
- 基础 U/Rack/Device Reader；
- Golden Sample 测试框架。

### Day 2

- Mapping；
- 双向同步基础；
- 冲突检测；
- Backup/Validate/Rollback；
- 简单 GUI；
- Skill 初版；
- Windows/macOS 基础验证。

## 15. 当前明确的工程优先级

真正关键的三个里程碑不是 GUI：

1. **Reader 读得准**；
2. **Mapping 身份不乱**；
3. **Sync 写得安全**。

只要这三关过了，GUI、Skill、打包更多是入口和体验问题。

## 16. Phase 0 当时尚未完成的调研条件（历史）

该调研会话当时只提供了机柜图截图，**尚未把对应的原始 `.xlsx` 作为 RackTool Golden Sample
纳入项目**。

因此开发时必须补：

- 至少两份真实/脱敏 XLSX；
- 人工 expected 结果；
- 特殊颜色、预留、文本字段的语义说明。

任何 Codex 任务都不应凭截图之外的信息伪造真实 XLSX 规则。

后续 V0.1 私有验收已用一个真实机柜 workbook 内的两类不同 Sheet 布局补齐这一历史缺口；
资产清单不是第二个机柜 Golden，私有业务内容继续保留在 Git 忽略范围内。
