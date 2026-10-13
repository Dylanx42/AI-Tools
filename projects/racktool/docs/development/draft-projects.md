# 新建机柜项目与设备编辑（Core/CLI）

这条流程从零创建机柜项目，不读取或写回已有业务 Excel。当前先提供 Core/CLI，GUI 后续接入。
项目 SQLite 保存设备身份与位置，Excel 用来查看和分享；请同时保留 SQLite。

## 命令行流程

安装 RackTool 后运行：

```bash
# 默认 A01–A18、B01–B18，每柜 42U；已有项目文件不会被覆盖
racktool project create new-project.sqlite --count 18 --height 42
# --row 是从 1 开始的排号；现有排后面可以继续增加新一排
racktool project add-rack new-project.sqlite C01 --row 3 --height 47
racktool project add-device new-project.sqlite --rack A01 --start-u 41 --end-u 42 --text "核心交换机 2U"
racktool project show new-project.sqlite
# 将 DEVICE_ID 替换为上一步输出中的 device_id；柜名或柜 ID 都可作为目标
racktool project edit-device new-project.sqlite DEVICE_ID --text "核心交换机 更新型号"
racktool project edit-device new-project.sqlite DEVICE_ID --rack B01 --start-u 35 --end-u 36
racktool export new-project.sqlite new-project.xlsx
```

`--count` 是每排数量（1–99），`--height` 是高度（1–100U）。追加机柜支持现有排和紧接其后的
新排，柜名大小写不敏感且必须唯一。设备可同名，但修改必须使用稳定 device_id。
设备位置修改支持重新指定机柜、U 范围及高度；改 U 时必须同时提供起始和结束 U，重叠和越界
会被拒绝，项目文件保持原样。仅修改机柜时保留原 U 范围，仍做目标冲突检查。

这些编辑命令会更新指定的新建项目 SQLite，不改 XLSX。命令输出 UTF-8 JSON，便于脚本调用；
`project show` 只读取。`export` 默认不覆盖已有输出，必要时显式使用 `--force`。

## Python 多行文字示例

```python
from pathlib import Path
from racktool.core import create_draft_project, add_draft_device, export_project_workbook

database = Path("new-project.sqlite")
create_draft_project(database, count=18, height_u=42)
project = add_draft_device(database, "A01", 41, 42, "核心交换机\n型号\n管理口")
export_project_workbook(project, Path("new-project.xlsx"))
```

设备文字原换行保留；以 `=` 开头的显示文字在标准导出中也作为文本保存，不执行公式。

## 与现有项目的边界

- `project import` 得到的是已绑定源 XLSX 的项目，不能使用这组新建项目编辑命令。
- 已绑定项目的设备移动继续使用 `sync move` / GUI 待同步与 Safe Sync；新增、改名写回尚待设计。
- 新项目的内部 Mapping 是虚拟布局坐标，不是导出 XLSX 的实际单元格位置。
- 新项目 ID 在同一个 SQLite 内保持稳定；导出再 import 会形成另一份项目身份，不能代替保留
  原 SQLite 的备份。
- GUI 目前只打开绑定 XLSX 的项目；可打开导出 Excel 查看机柜，但尚不能直接打开此新建 SQLite
  继续编辑。GUI 新建/设备编辑入口将复用已经验证的 Core API。

协议与保存保护见 [ADR-012](../decisions/ADR-012-draft-project-editing.md)。
