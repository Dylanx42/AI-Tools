# 命令参考

使用已安装 RackTool 的 Python 执行 `python -m racktool`。下列占位参数必须替换成真实路径与
模型 ID，参数用数组传给 subprocess，或正确 shell 引号；不要把业务文字拼成 shell 代码。

```bash
python -m racktool analyze source.xlsx
python -m racktool analysis-package source.xlsx analysis.zip
python -m racktool profile validate layout.yaml
python -m racktool profile apply source.xlsx layout.yaml
python -m racktool project import working.xlsx project.sqlite
python -m racktool project import working.xlsx project.sqlite --profile layout.yaml
python -m racktool project show project.sqlite
python -m racktool project rescan working.xlsx project.sqlite
```

同步命令默认是只读预览；检查计划后在同一组参数加 `--commit`：

```bash
python -m racktool sync move working.xlsx project.sqlite DEVICE_ID RACK_ID 21 22
python -m racktool sync add-device working.xlsx project.sqlite RACK_ID 21 22 --text "设备完整文字"
python -m racktool sync rename working.xlsx project.sqlite DEVICE_ID --text "更新后的完整文字"
python -m racktool export project.sqlite result.xlsx --layout source
python -m racktool export project.sqlite standard.xlsx --layout standard
```

导出默认不覆盖，已有目标请选新名字。只有用户明确要求覆盖该输出才加 `--force`。
Safe Sync 自动备份、临时写入、重载校验、提交并更新 SQLite；失败报告实际错误，不重复重试冲突。
源文件在外部改变后使用 rescan 保持身份，不能不检查就重新 import 覆盖既有项目。

新建未绑定项目：

```bash
python -m racktool project create draft.sqlite --count 18 --height 42
python -m racktool project add-rack draft.sqlite C01 --row 3 --height 47
python -m racktool project add-device draft.sqlite --rack A01 --start-u 21 --end-u 22 --text "服务器"
python -m racktool project edit-device draft.sqlite DEVICE_ID --text "服务器新名称"
python -m racktool project edit-device draft.sqlite DEVICE_ID --rack B01 --start-u 31 --end-u 34
python -m racktool export draft.sqlite draft.xlsx
```

新建项目命令直接保存 SQLite，导出产生 Excel；重新导入导出文件形成另一份身份，不能代替
保留 SQLite。新建项目没有原始版面，因此不能使用 `--layout source`。

同 Sheet 不同机柜可移动；不同机房 Sheet 之间的现有设备移动尚不支持，说明限制并停在建议。
