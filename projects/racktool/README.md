# RackTool

RackTool 是一个跨平台、离线优先的 Excel 机柜管理工具。它最终将以统一的 RackCore
连接 CLI、桌面界面和可选的 Agent 工作流，同时把结构化机柜数据作为事实层。

## 当前状态

**V0.5 Local GUI 已通过本地自动化门禁**。V0.1 负责只读扫描，V0.2 负责 YAML Profile，V0.3 负责稳定身份，
V0.4 负责安全写回，V0.5 增加不嵌入 Agent 的本地驾驶舱：

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
racktool gui path/to/rack-layout.xlsx
```

## CLI

```bash
racktool inspect path/to/workbook.xlsx
racktool analyze path/to/rack-layout.xlsx
racktool profile validate path/to/profile.yaml
racktool profile match path/to/rack-layout.xlsx path/to/profile.yaml
racktool profile apply path/to/rack-layout.xlsx path/to/profile.yaml
racktool project import path/to/rack-layout.xlsx path/to/project.sqlite
racktool project rescan path/to/rack-layout.xlsx path/to/project.sqlite
racktool sync move path/to/rack-layout.xlsx path/to/project.sqlite DEVICE_ID RACK_ID START_U END_U
racktool sync move --commit path/to/rack-layout.xlsx path/to/project.sqlite DEVICE_ID RACK_ID START_U END_U
racktool gui path/to/rack-layout.xlsx
# 或
python -m racktool inspect path/to/workbook.xlsx
python -m racktool analyze path/to/rack-layout.xlsx
```

命令把 UTF-8 JSON 写到标准输出。输入必须是现有的 `.xlsx` 文件；扫描过程只读取工作簿内容，
inspect/analyze/profile/project 默认只读取工作簿；`sync move --commit` 才会在备份和校验后写回。

## 明确不支持

当前不包含资产表对账、Agent/云 API、Shape/SmartArt、VBA、Office COM，或跨 Sheet 设备移动。

项目约束和后续设计见[产品需求](docs/product/requirements.md)、
[架构总览](docs/architecture/overview.md)、[数据模型](docs/architecture/data-model.md)和
[路线图](docs/roadmap/ROADMAP.md)。

## Golden Samples

两类真实布局已在 Git 忽略的 `samples/private/` 完成人工异常确认、源文件修正、结构审计和
Sheet 级 expected JSON 回归。私有材料不会进入 Git；以后提交公开回归样本前仍需脱敏。

自动化 V0.5 已通过。后续未知布局工作流和 Skill 必须保持 V0.1 到 V0.5 regression 通过。
