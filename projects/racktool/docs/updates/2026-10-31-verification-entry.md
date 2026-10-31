# 2026-10-31：整理功能验证入口并复跑完整 CLI 流程

## 触发与结果

已有源码检查、独立包脚本和实际 Agent 验收记录分散在多个入口；用户要求按功能整理验证表，
复用现有脚本，实际跑通一条完整流程，再提交 PR。

本轮增加[功能验证入口与证据表](../gates/feature-verification.md)，从项目 README 和 gates 索引进入。
重点覆盖预览/落实、歧义定位、冲突与旧请求拒绝、原项目恢复、位置表保存回导五条用户路径，
列明操作入口、可观察结果、现有测试和实际 Agent/Excel/WPS 边界。保留历史 gates，明确其日期和范围。
未修改 Core、CLI、验证脚本、已安装 Skill 或 CI，不发布新包。

## 本次执行环境

- 日期：2026-10-31，北京时间。
- 平台：macOS 27.2 / arm64，Python 3.11.9。
- 源码基线：`14566b441e7504c860589860a61bb6609b90634f`；新建 `docs/racktool-verification-entry` 工作区。
- 当前工作区独立 `.venv`，实际导入路径核对为该工作区的 `projects/racktool/src/racktool/__init__.py`。
  本轮源码与脚本未改变；文档变更不构成已安装正式包更新。
- 通过现有 `python3.11 scripts/dev.py setup` 安装约束文件中的开发依赖，未安装可选 Qt。
  初次沙箱内安装因网络限制失败；允许联网后原命令成功，未修改约束或换用全局旧包。
- 仅合成输入；当前新工作区未接入私有 Golden。未读取、复制或修改真实业务工作簿。

证据保存在本机原有主 checkout 的 Git 忽略目录 `samples/private/verification/2026-10-31-entry/`
（相对 `projects/racktool/`），独立于本任务临时 worktree。包含 `run-context.json`、源码检查日志、
`source-workflow/` 和 `independent-readback.json`。公开只提交本摘要，不提交 token、密钥、SQLite 或运行文件。

## 完整流程与独立核对

在新工作区 `projects/racktool/` 使用以下既有入口；变量值替换为上述证据根的绝对路径：

```bash
RACKTOOL_EVIDENCE="/绝对路径/2026-10-31-entry"
.venv/bin/python scripts/verify_skill_workflows.py --output "$RACKTOOL_EVIDENCE/source-workflow"
python3.11 scripts/dev.py check
```

脚本 **PASS：6 项检查，21 次实际 CLI 子进程调用**。`report.json` 的 scope 为 `scripted-cli-synthetic`。

| 路径/阶段 | 本次实际结果 |
| --- | --- |
| 布局与读图 | 明确坐标 Profile 校验和 Hash 绑定导入通过；双机房、同名设备、相反 U 方向及空闲区间匹配预设 |
| F2 同名歧义 | 仅给设备文字时拒绝，工作副本和 SQLite Hash 不变 |
| F1 预览与落实 | 预览不改业务文件；错误 token 拒绝；有效计划将原 Room-Z/A01 设备移到 Room-A/B01 的 2–4U，改为 3U 和 `MOVED-SYNTHETIC`，ID 保持 |
| F3 重放与占用 | 已用计划拒绝；6–8U 与另一设备占用重叠时拒绝，两业务文件不变 |
| F4 进程恢复 | 每次 CLI 从相同 SQLite 读回；后续查询/编辑保持身份。这是进程边界验证，不是本轮新 Agent 会话验收 |
| F5 导出与回导 | 原版面导出保留原 worksheet 字节；脚本模拟位置表编辑后预览/提交，同一设备回到 Room-Z/A01 的 1–2U，改名 `RETURNED-SYNTHETIC`；旧表再次预览拒绝 |

脚本成功后额外执行 `project show`，并从最终项目新导出 `final-source.xlsx`、`final-standard.xlsx`，
共 3 次 CLI 调用。未将已经消费的 `positions.xlsx` 当作最终导出。
使用标准库只读检查 XLSX XML，并与脚本预先确定的坐标/状态核对；独立结果 **12 项检查通过**：

- 原始输入 Hash 保持；额外查询和导出不改变工作副本或 SQLite。
- 两台设备 ID 集合与初始查询相同。
- 最终返回设备在降序机柜的 `D14:D15`（1–2U），原位置与中间位置清空。
- 另一设备保持在升序机柜的 `D9:D10`（6–7U）；两柜 U 标尺方向保持。
- 最终原版面导出与工作副本原 worksheet 部件字节一致；两种新导出都含两个机房和设备位置表。
- 两次写入的恢复备份实际存在于隔离的 `runtime/` 目录。

原始合成输入 SHA256：`d940a92ca75e42c1dcef9f864041f27d26e2d92a67763529646c7cf837627b8c`。
该值标识本次输入；生成器创建的 ZIP 时间戳可能使另一次生成的文件 Hash 不同，不能作为通用 Golden Hash。
六项脚本检查、21 次调用和十二项独立核对分别计数，不与 pytest 用例数相加。

## 源码与文档检查

`python3.11 scripts/dev.py check` 退出码 0：

- pytest：**614 passed、5 skipped、1 warning**，175.94 秒。
- warning 来自已有“工作表扩展写入前拒绝”测试中 openpyxl 对未知扩展的提示，该回归通过。
- 跳过：可选 PySide6 GUI 模块 1 项；未安装 Golden 1 项、私有 Profile 1 项、私有机房导出 2 项。
  缺少私有输入不算真实图通过，未使用 `--require-private`。
- Ruff、strict mypy（46 个源码文件）、依赖一致性及 CLI `--help` 均通过。
- 四份变更 Markdown 的 67 个本地链接/锚点有效，`git diff --check` 通过。

脚本完整流程与独立核对已在上节单独记录；本次文档修改没有新增镜像测试或重复执行框架。

## 剩余验收边界

- 本轮没有重新验收已安装正式 Release。源码测试中的临时包检查也不是正式发行包的本机验收。
- 实际新 Agent 会话的已有证据仍是[2026-10-30 合成验收](2026-10-30-agent-recovery-acceptance.md)，
  不将历史结论改成此次重新通过，也不改写脚本报告中的 Agent pending。
- 真实图兼容性、Windows 实机、Excel/WPS 打开保存/元数据/版式/打印、WorkBuddy/TRAE 仍待验收。
  当前 Qt 可选客户端不在任务范围；未改变此前 GUI 人工验收结论。
- 功能、命令或执行环境变化时，更新验证表对应行并复跑受影响路径；产品失败独立记录，不放宽通过条件。
