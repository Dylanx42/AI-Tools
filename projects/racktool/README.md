# RackTool

RackTool 是一个跨平台、离线优先的 Excel 机柜管理工具。它最终将以统一的 RackCore
连接 CLI、桌面界面和可选的 Agent 工作流，同时把结构化机柜数据作为事实层。

## 当前状态

**V0.1～V0.5 automated gates PASS**。V0.1 负责只读扫描，V0.2 负责 YAML Profile，V0.3 负责
稳定身份，V0.4 负责安全写回，V0.5 提供不嵌入 Agent 的本地驾驶舱。旧的表格式 GUI 在 macOS
人工检查中因可用性不达标被拒绝，现已重构为：

- 总览、机柜、设备和异常四个工作页面；
- 单机柜可视化与友好的设备详情；
- 搜索和最多 100 行的有界设备列表；
- 带 RackCore 实时冲突检查的移动抽屉；
- 不提前修改 XLSX 的待同步队列；
- 统一从顶部“同步更改”进入 Safe Sync 批量事务；
- 由 RackCore 生成含“机柜图”和“设备位置表”的独立 Excel 导出，保留多行文字，设备表可筛选。

底层 Reader 当前能够：

- 按原始顺序列出工作表；
- 提取非空单元格、坐标、数据类型和稳定的常见样式签名；
- 提取实际内容范围、openpyxl 报告的维度、合并区域、显式行高和列宽；
- 检测连续整数 U 轴；
- 结合 U 轴与相邻合并标题形成机柜候选；
- 将设备区文本及合并高度映射为 Rack/U/来源范围候选；
- 以确定性 JSON 输出扫描和候选分析结果。

Profile 只描述布局规则，不保存设备业务数据。错误、冲突或低置信度 Profile 不会被静默应用。

候选结果保留置信度和 evidence，**不等于人工确认的业务真值**。重复标题、错误名称、忽略标签、
颜色语义和资产表对账仍需单独验证；synthetic fixture 也不构成真实格式兼容性的证据。

当前完整套件为 155 passed；PySide6 headless 和真实私有工作簿副本的 macOS native launch 已完成。
新版 macOS GUI 用户验收、Windows GUI 检查，以及 Microsoft Excel/WPS 实机打开和写回仍为
**MANUAL VALIDATION PENDING**，不能由自动化或启动成功替代。
完整证据见 [V0.5 Integrated Audit](docs/gates/V0.5-integrated-audit.md)。

## 安装与验证

需要 Python 3.11 或更高版本：

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

本地驾驶舱需要额外安装 Qt：

```bash
python -m pip install -e '.[gui]'
racktool-gui
racktool gui
racktool gui path/to/rack-layout.xlsx
```

`racktool-gui` 和不带路径的 `racktool gui` 默认打开空项目，不会自动载入示例、测试或最近使用的
工作簿；只有用户点击“打开…”或明确传入 `.xlsx` 路径后才读取数据。

GUI 的项目数据库和 Safe Sync 恢复备份默认保存在操作系统的 RackTool 应用数据目录，不会在源
Excel 旁边生成 `.sqlite`、`.sqlite.bak-*` 等实现文件。真实写回前的 Excel 恢复备份仍会保留，
但每个工作簿最多 3 份、最长 30 天；数据库事务备份在成功或成功回滚后立即删除，异常中断残留
最长保留 7 天。应用会在启动或打开项目时自动清理，无需后台常驻进程。旧版同目录项目文件会在
下次打开对应工作簿时经过校验后迁移；内容冲突时不会自动覆盖。

## CLI

```bash
racktool inspect path/to/workbook.xlsx
racktool analyze path/to/rack-layout.xlsx
racktool profile validate path/to/profile.yaml
racktool profile match path/to/rack-layout.xlsx path/to/profile.yaml
racktool profile apply path/to/rack-layout.xlsx path/to/profile.yaml
racktool project import path/to/rack-layout.xlsx path/to/project.sqlite
racktool project import path/to/rack-layout.xlsx path/to/project.sqlite --profile path/to/profile.yaml
racktool project rescan path/to/rack-layout.xlsx path/to/project.sqlite
racktool sync move path/to/rack-layout.xlsx path/to/project.sqlite DEVICE_ID RACK_ID START_U END_U
racktool sync move --commit path/to/rack-layout.xlsx path/to/project.sqlite DEVICE_ID RACK_ID START_U END_U
racktool export path/to/project.sqlite path/to/racktool-export.xlsx
racktool gui path/to/rack-layout.xlsx
# 或
python -m racktool inspect path/to/workbook.xlsx
python -m racktool analyze path/to/rack-layout.xlsx
```

命令把 UTF-8 JSON 写到标准输出。输入必须是现有的 `.xlsx` 文件。`inspect`、`analyze` 和
`profile` 不修改源工作簿；`project import` 的 `--profile PATH` 是可选参数。`project import/rescan`
也不写 XLSX，但会创建或更新 SQLite 项目状态。
只有 `sync move --commit` 会在冲突检查、备份、临时写入、重载校验后事务式更新 XLSX 和 SQLite。
`export` 只读取已保存的项目状态，新建一个含“机柜图”和“设备位置表”的标准 `.xlsx`；它通过
临时文件、重载验证和原子替换生成导出文件，不写源工作簿。命令行默认不覆盖已有导出，确需覆盖时
显式增加 `--force`；GUI 的“导出表格”由系统保存对话框确认文件名，原有 JSON 导出保留在文件菜单。

## 明确不支持

当前不包含资产表对账、Agent/云 API、Shape/SmartArt、VBA、Office COM，或跨 Sheet 设备移动。

项目约束和后续设计见[产品需求](docs/product/requirements.md)、
[架构总览](docs/architecture/overview.md)、[数据模型](docs/architecture/data-model.md)和
[路线图](docs/roadmap/ROADMAP.md)。

## Golden Samples

一个真实私有机柜 workbook 中的两类不同 Sheet 布局已在 Git 忽略的 `samples/private/` 完成
人工异常确认、源文件修正、结构审计和 Sheet-scoped expected JSON 回归。资产清单 workbook 只作
独立对账，不是第二个机柜布局 Golden。私有材料不会进入 Git；以后提交公开回归样本前仍需脱敏。

原 V0.1 的 90 racks / 710 device anchors / 710 placements 是历史完整结构审计；本次独立审计的
当前 private regression 为 3 passed，不得把 synthetic fixture 或测试计数改写成额外真实 Golden。

V0.1～V0.5 automated gates 已通过。后续未知布局工作流和 Skill 必须保持相同 regression 绿色，
并继续明确区分自动化结果与待完成的实机人工验证。
