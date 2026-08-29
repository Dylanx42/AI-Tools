# RackTool Profile 设计

## 1. Profile 的目的

Profile 用于描述“某类 XLSX 机柜图的布局规则”。

它解决的问题是：

- 同一业务含义可能有不同 Excel 排版；
- 第一次需要理解，后续不应重复猜测；
- 人工和 Agent 都应该能生成/修改规则；
- 规则应可进入 Git 共享。

Profile **不是设备清单，不保存具体设备业务数据**。

## 2. 设计目标

- 人可读；
- 可版本控制；
- 可校验；
- 可解释；
- 允许局部规则而非写死整张表坐标；
- Agent 能生成；
- RackCore 能确定性执行。

建议格式：YAML。

## 3. 基础结构草案

```yaml
schema_version: 1
profile_id: legacy-layout-01
name: Legacy IDC dual-U-axis layout

match:
  sheet_name_regex: ".*机柜.*"
  min_confidence: 0.80

rack:
  title:
    mode: merged_cell_above_u_axis
  height:
    mode: infer_from_u_axis

u_axis:
  duplicated: true
  direction: descending
  allowed_heights: [42, 47, 48, 53]

device_area:
  mode: between_u_axes

text:
  ignore_exact:
    - "空闲"
    - "预留"

style:
  color_is_semantic: false
```

这只是 schema 草案，不是最终代码契约。

## 4. 两类规则

### 4.1 结构规则

例如：

- U 轴连续数字；
- 左右重复 U；
- 设备区域位于两轴之间；
- 机柜名在 U 轴上方；
- 设备以合并单元格为主要对象。

这类规则应优先使用。

### 4.2 坐标规则

当某些旧表极其固定时，可允许：

```yaml
rack:
  title_range: "F3:I3"

u_axis:
  left_column: "F"
  right_column: "I"

device_area:
  range: "G4:H50"
```

但坐标规则可移植性较差，应尽量作为 fallback。

## 5. Profile 匹配

建议 RackCore 先生成 Workbook Fingerprint/Feature Summary：

- Sheet 名称；
- 合并区域统计；
- 连续整数列；
- U 候选高度；
- 左右重复轴特征；
- 设备合并区域密度；
- 标题位置特征。

Profile Matcher 返回：

```text
profile_id
match_score
reasons[]
```

低于阈值不自动应用。

## 6. 置信度原则

推荐三个等级：

- High：可自动应用；
- Medium：生成候选并要求确认；
- Low：导出分析包/手工定义。

实际阈值后续通过测试调整，不在文档中硬编码固定百分比。

## 7. Agent 生成 Profile

Skill/Agent 的流程：

```text
Analysis Package
 ↓
Agent 分析结构
 ↓
生成 Profile YAML
 ↓
RackCore profile validate
 ↓
RackCore 在样本上 dry-run
 ↓
输出识别摘要
 ↓
用户确认
```

Agent 不允许直接声称“规则正确”而跳过 RackCore 验证。

## 8. Profile 校验

至少检查：

- schema_version；
- 必填字段；
- 列/范围合法；
- direction 合法；
- allowed_heights 合法；
- 规则无明显互斥；
- 应用后 U 映射合理；
- 不跨出 Worksheet 范围。

## 9. Profile 与业务数据分离

禁止把这些内容写进共享 Profile：

- 某台具体设备名；
- 某个项目的敏感 IP；
- 具体机密业务数据；

除非该信息是用于 fixture 且已脱敏。

## 10. 公共 Profile 库

仓库未来可包含：

```text
profiles/
├── generic-single-axis.yaml
├── generic-dual-axis.yaml
├── nmidc-standard.yaml
└── legacy-xxx.yaml
```

新 Profile 提交要求：

- 至少一个 fixture；
- expected 解析结果；
- 说明适用范围；
- 不包含敏感原始数据。

## 11. Profile 不应做的事

Profile 不应：

- 直接执行 Python 任意代码；
- 带 shell 命令；
- 绕过校验写文件；
- 变成客户特例堆栈；
- 替代领域数据模型。

如果规则复杂到 YAML 无法表达，应先评估是否需要通用 Parser 能力，而不是不断扩展任意脚本字段。
