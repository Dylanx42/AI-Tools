# RackTool 数据模型设计

## 1. 设计原则

1. 结构化数据表达事实；
2. Excel 坐标表达来源/映射，不表达唯一身份；
3. 设备显示文本可以变化；
4. Rack/U Placement 是核心业务关系；
5. 所有模型可序列化、可测试；
6. 不把 GUI 或 Excel 对象直接塞进领域模型。

## 2. 核心实体

### 2.1 Rack

建议字段：

```text
Rack
├── rack_id: str
├── rack_name: str
├── height_u: int
├── source_sheet: str | null
├── bounds: CellRange | null
├── u_axis: UAxisDefinition | null
├── device_area: CellRange | null
├── profile_id: str | null
└── confidence: float | null
```

约束：

- `height_u > 0`
- `rack_id` 稳定，不因显示名称变化而自动改变；
- `rack_name` 是用户可见名称。

### 2.2 Device

```text
Device
├── device_id: str
├── display_text: str
├── canonical_name: str | null
├── attributes: dict[str, Any]
└── source_identity: SourceIdentity | null
```

说明：

- V1 不强迫从多行文本中自动猜出型号/IP/主机名；
- `display_text` 应尽量保留原单元格信息；
- 以后可增加文本解析器把 IP/型号拆成 attributes。

### 2.3 Placement

Placement 表示“某设备放在哪个 Rack/U”。

```text
Placement
├── placement_id: str
├── device_id: str
├── rack_id: str
├── start_u: int
├── end_u: int
├── height_u: int
├── orientation: str | null
└── status: str
```

建议统一规则：

```text
height_u = abs(end_u - start_u) + 1
```

但要明确 U 方向可能在 Excel 行号中是倒序的，因此业务 U 数值与 Worksheet Row 不应混为一谈。

### 2.4 SourceMapping

```text
SourceMapping
├── mapping_id: str
├── device_id: str | null
├── rack_id: str | null
├── workbook_fingerprint: str
├── sheet_name: str
├── source_range: str
├── mapping_kind: str
├── style_signature: str | null
└── confidence: float | null
```

作用：

- 记录 Excel 中设备对象来自哪个 range；
- 支持重新扫描后匹配；
- 支持写回；
- 允许 display_text 变化而身份仍可追踪。

### 2.5 RackProject

```text
RackProject
├── project_id: str
├── source_workbook: str | null
├── workbook_fingerprint: str | null
├── racks: list[Rack]
├── devices: list[Device]
├── placements: list[Placement]
├── mappings: list[SourceMapping]
├── profile_refs: list[str]
└── metadata: dict[str, Any]
```

## 3. 辅助模型

### 3.1 CellRange

```text
CellRange
├── min_row: int
├── max_row: int
├── min_col: int
├── max_col: int
└── a1: str
```

### 3.2 UAxisDefinition

```text
UAxisDefinition
├── side: left | right | both | unknown
├── columns: list[int]
├── direction: ascending | descending
├── u_to_row: dict[int, int]
└── confidence: float
```

### 3.3 Candidate

自动识别阶段不要直接生成最终 Rack/Device，可先产生候选：

```text
RackCandidate
DeviceCandidate
UAxisCandidate
```

候选保留：

- evidence；
- confidence；
- reason codes；
- ambiguity。

这样 GUI/Agent 才能解释“为什么识别成这样”。

## 4. ID 策略

V1 建议：

- 新建实体使用 UUID 或稳定短 ID；
- 对从外部 Excel 首次导入的对象，可以基于 project + source range 生成初始候选 ID，但之后不应只靠 range 保持身份；
- 不使用 display_text 作为唯一 key。

示例：

```text
rack_id   = RACK-01H...
device_id = DEV-01H...
```

具体使用 UUIDv4/UUIDv7/ULID 由实现阶段决定；任何选择应保持可测试和跨平台。

## 5. Placement 不变量

必须保证：

1. `start_u` / `end_u` 都在 `1..rack.height_u`；
2. `height_u` 与范围一致；
3. 同一个 rack 中，不允许两个 active placement 占用同一 U，除非未来明确支持前后双面/特殊设备并新增模型；
4. 一个 device 默认只有一个 active placement；
5. 移动设备时保留 device_id。

## 6. Excel Row 与 U 的映射

必须显式建映射：

```text
U 47 → row 4
U 46 → row 5
...
```

而不是假设：

```text
U == row
```

因为：

- 标题会占行；
- U 方向可能倒序；
- 中间可能存在空行；
- 左右 U 轴可能重复；
- 不同机柜高度不同。

## 7. 设备文本策略

V1 默认：

- 合并区域内多行文本整体保留为 `display_text`；
- 不强制把第一行认定为设备名；
- 可选 `canonical_name`；
- Profile 可以给文本解析提示，但不能在低置信度时静默丢弃内容。

## 8. Mapping 生命周期

### 初次导入

```text
Range → Candidate → Device + Placement + SourceMapping
```

### 重新扫描

优先匹配：

1. 内部 metadata / stable id（若存在）；
2. source mapping / workbook fingerprint；
3. range + rack/U；
4. display text 仅作为辅助证据。

### 设备移动

```text
Device ID 不变
Placement 更新
SourceMapping 更新
```

## 9. Metadata 存储

讨论中考虑两类方式：

- SQLite；
- Excel 隐藏 Sheet（如 `_RACK_META`）。

V1 可以采用“SQLite 为项目状态 + 可选 workbook metadata”的组合，但具体写法应在 Mapping 阶段通过 ADR 确认。

当前硬要求只是：

> 必须存在稳定映射机制，不能每次都依赖 AI 或显示文本重新猜身份。

## 10. 序列化示例

```json
{
  "rack_id": "RACK-A01",
  "rack_name": "A01",
  "height_u": 53,
  "devices": [
    {
      "device_id": "DEV-000001",
      "display_text": "NMDC-PRD-CPU-13",
      "placement": {
        "start_u": 31,
        "end_u": 32,
        "height_u": 2
      },
      "source": {
        "sheet": "机柜图",
        "range": "B24:B25"
      }
    }
  ]
}
```

注意：示例中的具体 range 只是示意，不代表当前真实文件。
