# 合成布局与编辑验证矩阵（2026-10-13）

## 范围与实测结果

Linux 云端 / Python 3.12，完整 pytest：**484 passed、0 skipped**；Ruff、strict mypy 和
Qt offscreen 冒烟通过。完整套件包含原有私有 Golden/Profile 回归，不将其解释为额外 workbook。

独立生成并检查 **144 种布局组合 + 120 种新建项目编辑场景**，264 passed、0 failed。
完成 1152 次成功编辑和 528 次拒绝操作，交付包含 552 份原始、编辑后或标准导出的 XLSX。

| 基本布局结构 | 组合数 | 识别入口 |
| --- | ---: | --- |
| 双 U 轴、一列设备 | 24 | 默认 Reader |
| 双 U 轴、两列设备 | 24 | 默认 Reader |
| 相邻机柜共享 U 轴 | 24 | 默认 Reader |
| 仅一侧 U 轴的边缘机柜 | 24 | 默认 Reader |
| 同 Sheet 两排机柜 | 24 | 默认 Reader |
| 标题与设备区分离的坐标布局 | 24 | 显式 Profile |

每类组合覆盖升序/降序、12/42/47/53U、整数/ASCII `U` 后缀/全角 `Ｕ` 后缀（ASCII 数字，含
前导零）。同时改变来源偏移、合并宽度和行列尺寸。它们是 6 类结构的 144 种参数组合，
不是 144 种独立行业标准，也不是真实业务 Golden。

新建场景覆盖每排 1/2/3/6/18 柜、4 个高度、A01 初始占用比例 0/25/50%、多行文字/公式样式
文字两种形式。编辑阶段会加入必要占位对象用于冲突检查，因此最终占用率不等于初始配置值。

## 行为验证

- expected JSON 来自 fixture 的构造事实，不从当前 Parser 结果生成答案。
- 每种来源布局验证导入、移动、新增、改名、原始备份、重叠/越界拒绝、重扫 ID 保持与标准导出。
- 核对所有未触及的单元格值/类型/样式、U 标尺、行列尺寸，保留隐藏页、备注、超链接、命名区域
  以及原有公式；标准导出逐设备核对机柜和 U 位。
- 每个新建场景验证追加第三排、同名设备独立 ID、文字编辑、跨柜移动及高度调整、错误拒绝后
  SQLite 不变、重启读取与导出再识别。
- 额外聚焦测试覆盖注释/超链接/数据验证/命名区域、已有空白合并、Profile 忽略的未知数据、
  无效文字、过期/伪造计划、临时验证失败及 SQLite 保存失败后的双文件回滚。
- 发现并修复以 `=` 开头的普通文字在移动后变成公式的问题；旧基线 be766e5 的复现为
  1 failed / 1 passed，新实现保留文字与实际公式各自的类型。巨大越界 U 输入在遍历前拒绝。
- 旧基线允许将 NUL 等非法 XML 字符存入新建项目，随后 XLSX 导出报错；现在在所有文字编辑
  入口统一拒绝。补充非法控制字符、XML 非字符、无效 Unicode、合法 emoji/符号/TAB 与字面
  公式文字测试，失败时不修改 SQLite 或工作簿。

真实私有证据单独验证：在原业务工作簿的副本上，两种 Sheet 布局各完成一次新增和一次文字
编辑（4 次事务），验证备份、稳定 ID 和重扫结果；原始 Golden SHA256 未变、项目无错误。
私有副本、事务记录和数据只保留在 Git 忽略目录，不进入公开 ZIP、PR 或样本矩阵。

## 复现与样本交付

从源码项目目录安装开发依赖后执行：

```bash
python scripts/stress_layouts.py --output /path/to/new-evidence-directory
pytest tests/integration/test_layout_corpus.py
pytest tests/integration/test_safe_device_edits.py tests/integration/test_literal_device_move.py
```

脚本要求新的输出目录，并隔离恢复备份存储；生成逐案例的源/编辑后 XLSX、独立预期、验证 JSON、
Profile、CSV、汇总报告和 ZIP。ZIP 中不包含绑定云端路径的导入项目数据库；新建项目 SQLite
没有源绑定，可随新建样本交接。失败案例会被报告并返回非零状态，不改写 expected 来凑通过。

## 验收边界

这些是已运行的自动化证据，不代替真实私有 Golden 或 Microsoft Excel/WPS 的人工视觉、打印和
写回检查。Mac / Windows GUI 的新增和编辑入口、Windows ARM，以及正式发布验收仍待完成。
