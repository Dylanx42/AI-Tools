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
  "workbook": "source.xlsx",
  "analysis": {}
}
```

其中 `analysis` 必须是人工核对后的 `racktool analyze` 完整结构化结果，而不是未经复核的程序输出。
提交前必须完成脱敏，同时保留影响解析的 Sheet、坐标、合并关系、样式和行列尺寸。

未经人工确认或仍含客户、设备、IP、序列号、资产编号的数据只能放在 Git 忽略的
`samples/private/`，不能放入本目录。
