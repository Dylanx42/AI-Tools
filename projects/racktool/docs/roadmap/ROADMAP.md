# RackTool 开发路线图

## 当前门禁状态（2026-08-31）

- Phase 0：PASS，详见 `docs/gates/PHASE0.md`。
- V0.1 Reader：PASS，详见 `docs/gates/V0.1.md`。
- 两类真实私有布局已冻结 Sheet 级 expected JSON、源文件 Hash 和持久验收记录；本地 Golden
  regression 与完整结构审计通过。
- 当前阶段：允许开始 V0.2 Profile；后续门禁必须持续复跑 V0.1 regression。

## 1. 总体策略

开发顺序遵循：

> **先读准 → 再认身份 → 再安全写 → 最后做 GUI/Skill。**

不要把 GUI 漂亮程度当成早期完成度。

## 2. 版本路线

### Phase 0 / V0.0.x — 项目基础

目标：让 Codex 能在明确边界内开发。

产物：

- AGENTS.md；
- Requirements；
- Background Research；
- Architecture；
- Data Model；
- Profile Design；
- ADR；
- Python package skeleton；
- pytest 基础设施；
- CI 草案（可稍后）。

完成标准：

- 项目结构清楚；
- Codex 不需要猜核心架构；
- `pytest` 可运行；
- 真实 Golden Samples 缺失被明确记录，而不是伪造。

---

### V0.1 — Reader

目标：`.xlsx → 标准结构化数据`。

功能：

- workbook scanner；
- sheet/merged cells；
- U-axis candidate detector；
- rack candidate detector；
- device extractor；
- start/end/height U；
- JSON 输出；
- CLI `analyze` 基础能力。

验收：

- 至少两类真实 XLSX Golden Sample；
- expected JSON；
- regression tests。

---

### V0.2 — Profile

目标：陌生布局不靠不断加硬编码。

功能：

- YAML Profile schema；
- loader；
- validator；
- matcher；
- format fingerprint；
- manual profile application；
- dry-run。

验收：

- 至少一个样本通过通用自动识别；
- 至少一个样本通过 Profile 识别；
- Profile 错误不会静默写入数据。

---

### V0.3 — Identity & Mapping

目标：设备移动/改名后身份不乱。

功能：

- rack_id；
- device_id；
- placement；
- source mapping；
- SQLite 项目状态（若本阶段确认）；
- workbook fingerprint；
- re-scan identity matching。

验收：

- display_text 修改后 device_id 保持；
- 设备移动后 Mapping 更新；
- 重扫不会无故复制设备。

---

### V0.4 — Safe Sync

目标：结构化数据 ↔ XLSX 双向同步。

功能：

- Excel → model；
- model → Excel；
- conflict detection；
- merge/unmerge；
- style preservation；
- backup；
- temporary write；
- reload validate；
- rollback/failure protection。

验收：

- 真实 XLSX 修改后 Office/WPS 可正常打开；
- 冲突时拒绝写入；
- 故意制造校验失败时原文件不受损；
- regression tests 全通过。

---

### V0.5 — Local GUI

目标：普通同事无需 CLI 即可工作。

功能：

- 打开项目；
- 设备清单；
- 机柜视图；
- 异常项；
- Mapping；
- 修改 Rack/U；
- 冲突提示；
- 同步；
- 导出；
- 备份恢复。

后续增强：

- Drag & Drop；
- 更友好的机柜可视化。

---

### V0.6 — Unknown Layout Workflow

目标：本地 APP 与 Agent/人工通过文件协作。

功能：

- 低置信度检测；
- 手工定义规则；
- Analysis Package 导出；
- Profile 导入；
- Profile dry-run；
- 错误解释。

---

### V0.7 — RackTool Skill

目标：让支持 Skill 的 Agent 能直接辅助使用 RackTool。

功能：

- SKILL.md；
- references；
- examples；
- CLI 调用说明；
- Profile 生成工作流；
- Analysis Package 工作流。

要求：

- Skill 不复制 Parser；
- Skill 不直接绕过 RackCore 写 Excel。

---

### V0.8 / V0.9 — Cross-platform & Release

目标：可分享给公司同事。

功能：

- macOS Apple Silicon 打包；
- Windows x86-64 打包；
- Windows ARM 基础兼容；
- GitHub Actions；
- Release artifacts；
- Office/WPS 人工验证；
- README 使用说明。

---

### V1.0 — Stable

发布门槛：

- Reader 稳定；
- Mapping 稳定；
- Safe Sync 稳定；
- GUI 可用；
- Skill 可分享；
- Mac + Windows x86-64 实测；
- 两类以上真实机柜图长期 regression；
- Backup/Validate/Rollback 有测试；
- 不依赖 Agent 即可日常使用。

## 3. 48 小时集中开发建议

如果用户安排连续两个工作日：

### Day 1 — 发动机

优先级：

1. 项目骨架；
2. 数据模型；
3. Workbook Scanner；
4. U/Rack/Device Reader；
5. CLI analyze；
6. synthetic tests；
7. 接入真实 Golden Samples（若已提供）。

Day 1 结束目标：

```text
racktool analyze sample.xlsx
```

能输出稳定 JSON。

### Day 2 — 变成工具

优先级：

1. ID/Mapping；
2. conflict validator；
3. safe write-back 基础；
4. Backup/Validate；
5. 简单 GUI；
6. Profile 导入导出；
7. Skill 初版；
8. Windows/macOS 基础人工验证。

两天目标：**可用 Beta，不追求最终 GUI 美化和全部边角兼容。**

## 4. 三个真正的里程碑

### M1：读得准

Reader 能稳定从真实 XLSX 得到正确 Rack/U/Device。

### M2：身份不乱

改名、移动、重扫后 device_id / rack_id / Mapping 稳定。

### M3：敢写真实文件

写回具备冲突保护、备份、重载验证和失败保护。

只有 M1–M3 都成立，RackTool 才算真正“成了”。

## 5. 开发环境与验收

| 环境 | 角色 |
|---|---|
| Codex Cloud | 主开发 |
| GitHub AI-Tools/projects/racktool | 唯一代码事实来源 |
| MacBook Air | macOS 验收 |
| PD Windows 11 ARM | 快速 Windows 验收 |
| Lenovo R7000P x86-64 | 正式 Windows/Office/WPS 验收 |
| GitHub Actions | 自动测试和发布（后续） |

## 6. 暂不进入路线的事项

- OCR；
- PDF；
- Visio；
- Excel Shape；
- Web SaaS；
- GUI 内嵌 Agent；
- NetBox/CMDB；
- 商业账号/授权系统。
