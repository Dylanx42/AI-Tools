# Layout Profiles

这些 YAML 文件描述布局规则，不保存设备业务数据。

- `generic-dual-axis.yaml`：左右成对 U 轴、标题在轴上方、设备区夹在两轴之间。
- `generic-mixed-axis.yaml`：同一张图同时包含成对轴和边缘单轴机柜。

Profile 必须先通过 `racktool profile validate`。低置信度、冲突或错误 Profile 不会被自动应用。
