# 命令参考

独立包使用 Python 3.11+ 执行技能目录中的 scripts/run.py。下面为方便阅读使用相对路径；
实际调用时替换为脚本和业务文件的绝对路径。仓库开发环境改用 python -m racktool。
独立入口的输出编码固定为 UTF-8；调用方捕获/读取 JSON 时也使用 UTF-8。
占位 ID 从 Core 输出获取，参数用数组传给 subprocess 或正确 shell 引号，勿把业务文字拼成代码。

```bash
python scripts/run.py analyze source.xlsx
python scripts/run.py analysis-package source.xlsx analysis.zip
python scripts/run.py profile validate layout.yaml
python scripts/run.py profile apply source.xlsx layout.yaml
python scripts/run.py project import working.xlsx project.sqlite
python scripts/run.py project import working.xlsx project.sqlite --profile layout.yaml
python scripts/run.py project show project.sqlite
python scripts/run.py project rescan working.xlsx project.sqlite
```

同步命令默认是只读预览；检查计划后在同一组参数加 `--commit`：

```bash
python scripts/run.py sync move working.xlsx project.sqlite DEVICE_ID RACK_ID 21 22
python scripts/run.py sync add-device working.xlsx project.sqlite RACK_ID 21 22 --text "设备完整文字"
python scripts/run.py sync rename working.xlsx project.sqlite DEVICE_ID --text "更新后的完整文字"
python scripts/run.py sync edit working.xlsx project.sqlite DEVICE_ID RACK_ID 21 23 --text "更新后的完整文字"
python scripts/run.py export project.sqlite result.xlsx --layout source
python scripts/run.py export project.sqlite standard.xlsx --layout standard
```

导出默认不覆盖，已有目标请选新名字。只有用户明确要求覆盖该输出才加 `--force`。
Safe Sync 自动备份、临时写入、重载校验、提交并更新 SQLite；失败报告实际错误，不重复重试冲突。
源文件在外部改变后使用 rescan 保持身份，不能不检查就重新 import 覆盖既有项目。

新建未绑定项目：

```bash
python scripts/run.py project create draft.sqlite --count 18 --height 42
python scripts/run.py project add-rack draft.sqlite C01 --row 3 --height 47
python scripts/run.py project add-device draft.sqlite --rack A01 --start-u 21 --end-u 22 --text "服务器"
python scripts/run.py project edit-device draft.sqlite DEVICE_ID --text "服务器新名称"
python scripts/run.py project edit-device draft.sqlite DEVICE_ID --rack B01 --start-u 31 --end-u 34
python scripts/run.py export draft.sqlite draft.xlsx
```

新建项目命令直接保存 SQLite，导出产生 Excel；重新导入导出文件形成另一份身份，不能代替
保留 SQLite。新建项目没有原始版面，因此不能使用 `--layout source`。

已有绑定设备改高、跨机房移动走下述 conversation edit；同步入口也提供 sync edit。

## 对话协议（优先使用）

Agent 将用户自然语言转为 UTF-8 JSON 文件，然后调用确定性 Core；Core 不接收自由提示词。
所有业务路径使用绝对路径，JSON 用文件工具或 json.dump 生成，不能将设备文字拼进 shell。

```bash
python scripts/run.py conversation query project.sqlite --request query.json
python scripts/run.py conversation preview project.sqlite --request edit.json --plan plan.json
python scripts/run.py conversation apply project.sqlite plan.json --token TOKEN --commit
```

查询设备（`device` 是完整文字精确匹配，`contains` 才是子串搜索）：

```json
{"kind":"devices","selector":{"room":"东机房","rack":"A01","contains":"交换机"},"limit":50,"offset":0}
```

查询空闲 U 或机柜，把 kind 换为 `free` / `racks`；这些 selector 仅接受 room、rack、rack_id。
输出 total、rows 和 next_offset；设备定位可追加 start_u、end_u 精确匹配当前范围。同名对象
必须补充机房/机柜/U 位到唯一，不默认取第一个。内部 ID 可以来自结果，但不要要求用户提供。

改名、跨机房移动与高度调整统一是 edit：

```json
{"operation":"edit","selector":{"room":"东机房","rack":"A01","device":"交换机","start_u":21,"end_u":22},"target":{"room":"西机房","rack":"B01"},"start_u":31,"end_u":33,"text":"交换机新名称","write_scope":"working-copy"}
```

改名可省略 target 与 U；只移动/改高可省略 text。新增使用 add，省略 selector，必须提供
text、target 与 start_u/end_u。绑定项目 scope 只能是 working-copy 或 original-authorized；
原图覆盖必须确有授权，不能仅靠填写 scope 创造授权。未绑定草稿使用 draft。

preview 返回 `status: previewed`、summary、plan 和 token；在对话里解释 before/after。
只要求预览时停止；已明确授权的工作副本变更无需重复许可，apply 使用同一计划及 token。
不要用 sync 的另一组参数替代经过审阅的计划。计划请求/摘要被改、数据库或源变化、token 不符、
重复提交时拒绝；需从当前项目重新预览。成功结果给出 backup_path、新的 Hash 和新设备 ID。
成功后的标记、Hash 报告或锁清理失败会保持 applied，并返回 warnings；不要重复执行编辑，先 query
核对当前状态。锁未清理时确认无写入任务后再处理报告中的锁路径。
预览不改业务 SQLite/XLSX，但会创建新计划和 SQLite 旁密钥；这些私有状态不入 Git，密钥不输出、不发给模型。
新会话读取同一 SQLite 并 query，再 export；不重新 import 来代替恢复，不依赖旧聊天。

协议的 subprocess 回归通过不代表任何 Agent 真机发现/自然语言调用通过，按 LOCAL_ACCEPTANCE.md
分别记录 Codex、WorkBuddy、TRAE 实际证据。

## 陌生布局适配

```bash
python scripts/run.py layout inspect source.xlsx
python scripts/run.py layout propose source.xlsx layout.yaml --sheet "东机房" --profile-id east-room
python scripts/run.py layout check source.xlsx layout.yaml
python scripts/run.py project import working.xlsx project.sqlite --profile layout.yaml --expected-sha256 SHA256
```

先核对只读报告中的机柜、U 方向和设备数量，再使用候选规则。没有可靠候选时用户须补充
标题/U 轴/设备区坐标，propose 的 `--help` 列出这些参数；不得猜测或强制通过。
SHA256 来自 check 报告，复制后的 working.xlsx 内容须相同。每个不同 Profile 暂分别建项目。

## 设备位置表回导

```bash
python scripts/run.py export project.sqlite editable.xlsx --layout source
python scripts/run.py position-table preview project.sqlite editable.xlsx
python scripts/run.py position-table apply project.sqlite editable.xlsx --token TOKEN
```

用户在 Excel/WPS 修改新导出的设备位置表 B/C/D/E/F 后，先预览整批变化再提交同一 token。
D 范围如 `21-23U`，E 高度填 `3`；F 机房与 C 机柜共同定位。保留隐藏 ID、隐藏名字元数据
和全部原设备行。整表排序须包含隐藏列；不支持通过增删行新增/删除设备。
旧包导出的表没有回导基线，需要从当前项目重新导出。表被修改、项目变化或预览过期后重新预览。
