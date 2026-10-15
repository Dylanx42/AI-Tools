# Layout Profiles

这些 YAML 文件描述布局规则，不保存设备业务数据。

- `generic-dual-axis.yaml`：左右成对 U 轴、标题在轴上方、设备区夹在两轴之间。
- `generic-mixed-axis.yaml`：同一张图同时包含成对轴和边缘单轴机柜。

Profile 必须先通过 `racktool profile validate`。低置信度、冲突或错误 Profile 不会被自动应用。

## 陌生布局对话工作流

`layout inspect source.xlsx` 使用一次源字节快照，返回 SHA256、逐 Sheet 的 U 轴、机柜/设备候选、
异常和结构 Profile 建议。它始终要求人工核对；非空 Sheet 无候选不等于可以丢弃该页。
`layout propose` 将明确选择的 Sheet 布局生成 YAML，再执行既有 schema validate、实际 YAML
reload、match 和 apply dry-run；设备文字不会进入规则。`layout check` 可在导入前重复验证。

自动结构识别不成功时，可明确指定几何区域：

```bash
racktool layout propose source.xlsx room-a.yaml --sheet 'Room A' --profile-id room-a-layout \
  --title-range G2:H2 --left-axis F --right-axis I --start-row 4 --end-row 45 \
  --device-range G4:H45 --direction descending --expected-sha256 '<inspect报告SHA256>'
racktool layout check source.xlsx room-a.yaml --expected-sha256 '<inspect报告SHA256>'
# 核对候选后，导入时再次核验同一源Hash
racktool project import source.xlsx room-a.sqlite --profile room-a.yaml \
  --expected-sha256 '<inspect报告SHA256>'
```

成功报告给 `ready_for_import`，仍需核对 `selected_analysis`；低置信度、异常或歧义停在
`review_required`，没有绕过检查的 force。check/propose 返回码 1 表示待核对，0 表示规则可供
确认后导入；inspect 是信息查询，返回码 0 不代表布局已通过。

当前固定区域规则每个 Sheet 只描述一个机柜。多种布局的 Sheet 应分别生成、核对 Profile，
然后导入不同 SQLite 项目；同一项目的持久 schema 仍只有一个 Profile，不承诺合并异构规则。
共享规则前检查 Sheet 匹配表达式是否包含敏感名称，按需改成通用表达式并重新 check。
