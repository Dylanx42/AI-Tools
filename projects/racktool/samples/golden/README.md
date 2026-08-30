# Golden Sample Contract

每个可提交的真实回归样本使用一个独立目录：

```text
samples/golden/<layout-slug>/
├── source.xlsx
└── expected.json
```

`expected.json` 格式：

```json
{
  "schema_version": 1,
  "workbook": "source.xlsx",
  "workbook_sha256": "<sha256>",
  "analysis": {}
}
```

其中 `analysis` 必须是人工核对后的 `racktool analyze` 完整结构化结果，而不是未经复核的程序输出。
当一个真实工作簿包含多类独立布局时，可以使用 Sheet 级 Golden：

```json
{
  "schema_version": 1,
  "workbook": "source.xlsx",
  "workbook_sha256": "<sha256>",
  "scope": {"kind": "sheet", "name": "Layout A"},
  "analysis": {}
}
```

此时 `analysis` 是指定 Sheet 的完整结构化结果。回归测试也会读取 Git 忽略的
`samples/private/golden/*/expected.json`，用于无法公开原始数据但已经人工确认的本地正式门禁；
私有 Golden 仍必须记录源文件 Hash 和持久化验收依据，不能直接把一次运行输出当作正确答案。

提交前必须完成脱敏，同时保留影响解析的 Sheet、坐标、合并关系、样式和行列尺寸。

未经人工确认或仍含客户、设备、IP、序列号、资产编号的数据只能放在 Git 忽略的
`samples/private/`，不能放入本目录。
