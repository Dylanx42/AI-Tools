# 命令参考

独立包使用 Python 3.11+ 执行技能目录中的 scripts/run.py。下面为方便阅读使用相对路径；
实际调用时替换为脚本和业务文件的绝对路径。仓库开发环境改用 python -m racktool。
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

同 Sheet 不同机柜可移动；不同机房 Sheet 之间的现有设备移动尚不支持，说明限制并停在建议。
