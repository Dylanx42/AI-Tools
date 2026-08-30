# RackTool Samples

`samples/private/` 用于本机真实或脱敏前的 XLSX 验收材料，并由项目 `.gitignore` 排除。
不要把客户名称、设备名称、IP、序列号、资产编号或未经确认的业务映射提交到公开仓库。

人工确认但无法公开的正式回归样本可以放在 `samples/private/golden/<case>/`。测试会读取其中的
`expected.json`，但必须同时保存源文件 SHA-256 和验收记录；私有文件不会进入 Git。

可公开的回归样本必须先完成脱敏，并配套人工确认的期望结果。当前自动化测试使用运行时生成的
synthetic workbook，只验证通用结构算法，不把合成布局当作真实格式兼容性证据。
