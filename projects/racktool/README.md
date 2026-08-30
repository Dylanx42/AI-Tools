# RackTool

RackTool 是一个跨平台、离线优先的 Excel 机柜管理工具。它最终将以统一的 RackCore
连接 CLI、桌面界面和可选的 Agent 工作流，同时把结构化机柜数据作为事实层。

## 当前状态

当前是 **V0.1 Reader 的安全基础阶段**。目前只提供只读 `.xlsx` Workbook Scanner：

- 按原始顺序列出工作表；
- 提取非空单元格、坐标、数据类型和稳定的常见样式签名；
- 提取实际内容范围、openpyxl 报告的维度、合并区域、显式行高和列宽；
- 以确定性 JSON 输出扫描结果。

Scanner 只描述工作簿结构，**不声称已经识别机柜、U 轴或设备**。合并单元格、样式、
合成的 rack-like 布局也不构成真实格式兼容性的证据。

## 安装与验证

需要 Python 3.11 或更高版本：

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

## CLI

```bash
racktool inspect path/to/workbook.xlsx
# 或
python -m racktool inspect path/to/workbook.xlsx
```

命令把 UTF-8 JSON 写到标准输出。输入必须是现有的 `.xlsx` 文件；扫描过程只读取工作簿内容，
不会保存、写回或修改源文件。

## 明确不支持

当前不包含机柜/U/设备检测、Profile、Mapping、数据库、GUI、Agent/云 API、Shape/SmartArt、
VBA、Office COM、冲突检查或任何形式的 Excel 写回。

项目约束和后续设计见[产品需求](docs/product/requirements.md)、
[架构总览](docs/architecture/overview.md)、[数据模型](docs/architecture/data-model.md)和
[路线图](docs/roadmap/ROADMAP.md)。

## Golden Samples 阻塞项

真实或脱敏 Golden Sample `.xlsx` 及人工确认的机柜数、设备数和 Rack/U 期望结果仍待提供。
收到这些材料之前，不会根据截图或 synthetic fixture 推断真实工作簿规则；实际 Reader 检测和
回归验收仍被该材料阻塞。
