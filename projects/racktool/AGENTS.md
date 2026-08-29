# RackTool — AGENTS.md

> 本文件是 Codex / Agent 在 `AI-Tools/projects/racktool` 内工作的项目级约束。
> **作用：提供工作边界、架构原则、验证要求和文档导航；不要把它当成完整设计文档。**

## 1. 项目范围

- 当前项目目录：`/projects/racktool`
- 上级仓库是 `AI-Tools` monorepo。
- **除非用户明确要求，不得修改 `/projects/racktool` 以外的任何兄弟项目、顶层共享配置或历史文件。**
- 不要在 `projects/racktool/` 内再次 `git init`，不要创建嵌套 Git 仓库。

## 2. 开工前必须阅读

任何架构或核心代码修改前，按顺序阅读：

1. `docs/product/requirements.md`
2. `docs/research/background-research.md`
3. `docs/architecture/overview.md`
4. `docs/architecture/data-model.md`
5. `docs/architecture/profile-design.md`
6. `docs/roadmap/ROADMAP.md`
7. 与当前任务相关的 `docs/decisions/ADR-*.md`

若文档与代码冲突：

- 不要默默选择一边；
- 先指出冲突；
- 优先遵循已接受的 ADR；
- 需要改变架构决策时，新增或 supersede ADR，而不是静默改方向。

## 3. 核心架构原则

### 3.1 RackCore 是唯一核心

- Excel 解析、机柜/U 位识别、设备提取、Mapping、校验、同步、备份恢复等确定性能力全部属于 `RackCore`。
- GUI、CLI、Skill 只能调用 RackCore，不允许各自复制一套核心逻辑。
- RackCore **不得依赖 GUI、Agent、云 API、ChatGPT、Codex Runtime**。

### 3.2 本地 APP 不嵌入 Agent

- RackTool 本地应用必须离线可用。
- 不在 GUI 内嵌 Codex App Server、Agent Runtime 或强制模型调用。
- Agent/Skill 是独立入口，通过标准 Profile / JSON / XLSX / Analysis Package 与本地应用协作。

### 3.3 V1 输入范围

V1 只承诺：

- `.xlsx`
- 普通单元格
- 合并单元格
- 行/列尺寸、边框、字体、填充、对齐等常见样式

V1 不承诺：

- PDF / 图片 OCR
- Visio
- Excel Shape / SmartArt / ActiveX
- VBA / 宏自动化
- Windows COM / Excel COM
- Web 多人协作
- CMDB / NetBox / SNMP 自动发现

### 3.4 结构化数据是主数据

- 设备身份不能只依赖显示文本。
- 使用稳定 `device_id` / `rack_id`。
- Rack/U Mapping 是系统事实层；Excel 是输入、输出和可视化载体。

### 3.5 AI 不直接修改 Excel

AI/Skill 只允许：

- 分析未知布局；
- 生成或修正 Profile；
- 解释异常；
- 建议规则。

任何真实文件写操作必须由 RackCore 的确定性逻辑执行，并通过校验。

## 4. Excel 安全规则

任何写回 XLSX 的功能必须满足：

1. 不直接原地破坏源文件；
2. 创建可恢复备份；
3. 优先写入临时文件；
4. 写后重新打开并验证；
5. 校验失败则不替换正式文件；
6. 保留可追踪错误信息；
7. 目标 U 位冲突、越界、映射歧义时默认拒绝写入；
8. 未经明确设计，不得删除未知工作表、命名区域、备注或与 RackTool 无关的数据。

## 5. 跨平台约束

目标平台：

- macOS Apple Silicon
- Windows 11 ARM（快速兼容测试）
- Windows 10/11 x86-64（正式验收）

禁止在 RackCore 中引入：

- Windows-only API
- Office COM
- 硬编码 `C:\...`
- 依赖某个桌面 Excel/WPS 进程才能运行的逻辑

路径处理使用 `pathlib`。

## 6. 低依赖原则

- Offline-first / Local-first。
- 优先标准库和少量成熟依赖。
- 不引入 Docker、外部数据库服务、消息队列或云服务作为开发/运行前置条件，除非有新 ADR 批准。
- SQLite 可作为本地状态存储，但核心数据模型应保持可序列化、可测试。

## 7. 测试规则

### 7.1 每个解析 Bug 都要变成回归测试

修复解析问题时必须：

1. 添加最小复现 fixture 或 synthetic workbook；
2. 添加 expected 结果；
3. 证明修复前失败、修复后通过；
4. 确保既有 Golden Samples 不回退。

### 7.2 测试层级

至少保持：

- Unit tests：数据模型、U 计算、冲突检查、Profile 解析等；
- Integration tests：XLSX → 标准模型；
- Regression tests：真实/脱敏机柜图 Golden Samples；
- Write-back tests：写入后重新加载并验证。

### 7.3 完成任务前

在当前任务允许的范围内运行：

```bash
pytest
```

若项目后续引入 lint/type-check，则也必须运行相应命令。不要宣称“完成”但不报告测试结果。

## 8. Profile 规则

- Profile 是“陌生机柜图布局适配规则”，不是业务数据。
- Profile 使用人可读、可版本管理的 YAML（除非 ADR 变更）。
- 自动识别低置信度时应生成候选，不应强行猜测。
- Agent 生成 Profile 后，必须由 RackCore Validate 通过才能应用。
- Profile 应可纳入仓库共享，让一次适配惠及后续同类文件。

详见：`docs/architecture/profile-design.md`。

## 9. 代码组织建议

目标结构（可在实现中细化，但不要违背层次）：

```text
src/racktool/
├── core/
├── models/
├── profiles/
├── cli/
└── gui/
```

依赖方向应大体保持：

```text
GUI / CLI / Skill
       ↓
    RackCore
       ↓
 Models / Profile / XLSX adapter / Persistence
```

不得反向让 Core 依赖 GUI。

## 10. Codex 任务工作方式

- 一次任务尽量像一个清晰 GitHub Issue，范围明确、可验证。
- 不要在单个任务里同时重写 Parser、GUI、Skill 和打包。
- 并行任务不得同时大改同一核心模块。
- 先读现状再改，不要假设仓库是空的。
- 不要为了“看起来完整”提前实现 ROADMAP 后续阶段。
- 遇到信息不足时，优先做安全的基础设施和测试，不要编造真实机柜格式。

## 11. 当前关键事实

- 项目目标：开源/公司内部可共享的跨平台 Excel 机柜管理工具。
- 主开发计划：Codex Cloud + GitHub `AI-Tools/projects/racktool`。
- 本地设备用于验收：MacBook Air、PD Windows 11 ARM、Lenovo R7000P x86-64。
- 当前只有机柜图截图用于需求讨论；真正 Golden Sample `.xlsx` 需要在开发阶段补充。
- V1.0 不嵌入 Agent，不做商业 SaaS。

## 12. Definition of Done

一个任务只有在以下条件满足时才算完成：

- 实现范围与需求一致；
- 没有无关目录修改；
- 测试通过或明确说明无法运行的原因；
- 新行为有测试；
- 关键设计变化更新文档/ADR；
- 输出简洁的变更摘要、测试结果、已知限制和下一步建议。
