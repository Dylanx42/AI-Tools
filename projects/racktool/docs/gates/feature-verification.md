# RackTool 功能验证入口与证据表

适用：Skill → CLI → RackCore 当前路线。先选择被测对象，再按用户路径取证。
本页复用现有脚本、测试和[本地验收规范](../../skills/racktool/LOCAL_ACCEPTANCE.md)，不增加执行框架。
源码检查由 [dev.py](../../scripts/dev.py) 组织，完整 CLI 流程由
[verify_skill_workflows.py](../../scripts/verify_skill_workflows.py) 执行。
开发负责人和本地/云端交接以[本地优先规范](../development/local-first-workflow.md)为准。

## 1. 选择执行对象

| 被测对象 | 准备与健康检查 | 执行入口 | 能证明什么 |
| --- | --- | --- | --- |
| 当前工作区源码 | `scripts/dev.py setup`；核对解释器、`racktool.__file__` 和 Git 提交；CLI `--help` 成功 | 当前工作区 `.venv` 中的 `python -m racktool`；下方源码流程 | 本次源码的确定性行为 |
| 正式独立 Skill 包 | 按[安装说明](../../skills/racktool/INSTALL.md)取得完整 Release ZIP 并核对 SHA256；`scripts/run.py --verify`、`--bundle-info`、`--help` | 包内 `scripts/run.py`；下方包流程 | 指定包的完整性、独立运行和脚本工作流；源码检查不能替代 |
| 实际 Agent | 记录软件/模型、Skill 版本与实际 Core 路径；在该软件中发出自然语言请求 | [本地验收第二层](../../skills/racktool/LOCAL_ACCEPTANCE.md#第二层自然语言调用) | 实际定位、调用、授权理解和会话恢复；CLI 子进程不等于新 Agent 会话 |
| 实际 Excel/WPS | 记录软件版本、平台及输入/输出；使用工作副本 | [本地验收第三层](../../skills/racktool/LOCAL_ACCEPTANCE.md#第三层实际-excelwps) | 打开保存、隐藏元数据、版式和打印；Core 重开不能替代 |

本地安装包不会随 `main` 更新。开发验证不能默认调用全局旧包；包验收也不能靠源码路径通过。
GUI 仅在涉及保留客户端的变更时另行检查，不是当前 Skill 路线的前置条件。

## 2. 五条重点用户路径

表中“自动化”是可重复的验证入口，不是本次或所有平台已经 PASS。具体结果要绑定日期、平台和提交。
所有编辑使用隔离副本与同一 SQLite；不同任务不得并发操作同一个项目或桌面实例。

| 路径 | 用户目标与操作入口 | 可观察的通过条件 | 已有自动化入口 | 仍需实际验收的边界 |
| --- | --- | --- | --- | --- |
| F1 预览后落实编辑 | “先看看移动效果”；`conversation query → preview`，获授权后 `apply --commit → query → export` | 预览不改变业务 XLSX/SQLite；落实使用同一计划，位置/高度/文字与预览一致，设备 ID 保持；原始留存文件不变 | 完整脚本的预览/跨机房改高检查；[对话回归](../../tests/integration/test_conversation_loop.py)、[绑定编辑](../../tests/integration/test_bound_device_edits.py)、[纯改名](../../tests/integration/test_rename_consistency.py) | Agent 能区分“看看”与已授权落实；真实图版式。跨机房限同一 XLSX、同一 SQLite 内的 Sheet |
| F2 同名对象定位 | “修改这台设备”；查询候选，补足机房/柜名/U 位，再预览 | 同名歧义拒绝，不能选首项；副本/SQLite Hash 不变；补足选择条件后唯一定位 | 完整脚本的同名设备拒绝；[对话回归](../../tests/integration/test_conversation_loop.py) | Agent 是否追问真正缺少的信息；不会要求用户自行找内部 ID |
| F3 冲突与旧请求拒绝 | 移到占用位置，或重复提交旧计划 | 占用预检拒绝并给出冲突；错误 token、过期/篡改/已用计划拒绝；拒绝前后业务文件与数据库不变 | 完整脚本的错误 token、重放和占用拒绝；[对话回归](../../tests/integration/test_conversation_loop.py)、[Safe Sync](../../tests/integration/test_safe_sync.py) | Agent 能解释具体拒绝原因，不绕过 Core 改单元格或 SQL |
| F4 从原项目继续 | “继续刚才的项目”；新进程或实际新会话读取原 SQLite，再提交/查询 | 不重新 import/create；稳定身份与状态保持；待办计划使用原计划与项目辅助状态；已消费计划仍拒绝 | 完整脚本逐次 CLI 子进程读取同一数据库；[对话回归](../../tests/integration/test_conversation_loop.py) | 真正的新 Agent 会话单独验收；[2026-10-30 记录](../updates/2026-10-30-agent-recovery-acceptance.md)仅覆盖当时 macOS/Codex/正式包的合成场景 |
| F5 导出、保存和回导 | 从当前项目导出位置表，在 Excel/WPS 修改 B–F 列并保存；`position-table preview → apply → query` | 隐藏 ID/元数据保留；U 范围与高度一致；预览不写业务文件；提交后身份保持；旧表、缺元数据或冲突拒绝，无部分写入 | 完整脚本模拟位置表编辑；[回导回归](../../tests/integration/test_position_roundtrip.py)同时覆盖 source/standard；[机房导出](../../tests/integration/test_room_export.py) | 脚本模拟编辑不等于 Excel/WPS 保存；实际软件的元数据、修复提示、合并、颜色、过滤及打印仍单独验证 |

预览可能创建计划与项目辅助密钥；“不写入”专指业务 XLSX 和 SQLite，不能解释为磁盘零副作用。
F4 的业务身份不以 SQLite inode 判断，原子保存可替换文件。CLI 请求字段和 JSON 示例统一查
[命令参考](../../skills/racktool/references/commands.md)，不在此复制第二份协议。

其他已有功能的验证入口：

| 功能 | 当前入口与验证依据 |
| --- | --- |
| 读图、机房/机柜/U 方向和空闲区间 | `analyze`、`conversation query`；完整脚本的双机房/反向 U 检查；[扫描](../../tests/integration/test_workbook_scanner.py)、[分析](../../tests/integration/test_workbook_analyzer.py)、[Golden](../../tests/regression/test_golden_samples.py) |
| 陌生布局与 Profile | `layout inspect/propose/check`、带 `--expected-sha256` 的导入；完整脚本只证明给定坐标的合成布局；[布局适配](../../tests/integration/test_layout_adaptation.py)覆盖低置信和过期源拒绝 |
| 空机柜、草稿、新增设备 | `project create/add-rack`、`conversation` 的 add/edit；[草稿编辑](../../tests/integration/test_draft_project_editing.py)、[空机柜模板](../../tests/integration/test_empty_rack_template.py)、[绑定新增/改名](../../tests/integration/test_safe_device_edits.py)；完整脚本不覆盖全部新建流程 |
| 备份、回滚及包隔离 | [Safe Sync](../../tests/integration/test_safe_sync.py)、[绑定编辑](../../tests/integration/test_bound_device_edits.py)、[独立包回归](../../tests/integration/test_skill_bundle.py)；不能用一次成功写入证明所有失败恢复分支 |

## 3. 跑通一条完整源码流程

以下命令从 `projects/racktool/` 执行，使用 Python 3.11+。macOS 示例用 `python3.11`；
Windows 可用 `py -3.11` 建环境，后续解释器路径为 `.venv\Scripts\python.exe`。

```bash
python3.11 scripts/dev.py setup
git rev-parse HEAD
.venv/bin/python -c "import platform, sys, racktool; print(platform.platform()); print(sys.version); print(sys.executable); print(racktool.__file__)"
.venv/bin/python -m racktool --help
python3.11 scripts/dev.py check
```

先核对实际 Core 路径属于本工作区 `src/racktool`，否则停止并修正环境。首次建立环境跑完整基线；
涉及 GUI 才加 `--gui`。当前工作区已安装私有 Golden 时加 `--require-private`，否则记录跳过原因。
`check` 会运行 pytest、Ruff、strict mypy、依赖检查和 CLI 帮助；独立包回归可能需要联网取得依赖。

选择一个**尚不存在的绝对目录**保存流程证据；不要预建该目录，不要把输出重定向到尚未创建的目录内。
可以放到 Git 忽略的 `samples/private/verification/<唯一运行名>/`，也可放在工作区之外的私有证据目录。

```bash
.venv/bin/python scripts/verify_skill_workflows.py --output "/绝对路径/新的流程证据目录"
```

脚本已有拒绝覆盖保护；每次复跑使用新目录。不要使用 `python -O` 或开启 `PYTHONOPTIMIZE`，
该脚本用断言核验结果。实际执行链为：

1. 生成两个 12U 合成机柜：Room-Z/A01 降序，Room-A/B01 升序，均有同名设备；留存原件并复制工作副本。
2. 用明确坐标生成/校验 Profile，按源 Hash 导入单 Sheet；再另建主项目，查询双机房设备、方向和空闲区间。
3. 仅给同名设备时拒绝；唯一定位后预览移动、改高和改名，核对业务 XLSX/SQLite 不变；错误 token 拒绝。
4. 提交同一计划，将 Room-Z/A01 的设备移到 Room-A/B01 的 2–4U，新名称为 `MOVED-SYNTHETIC`，ID 保持。
5. 再次提交旧计划及预览占用区间均拒绝，工作副本和数据库不变。
6. 原版面导出 `positions.xlsx`，核对原 worksheet 部件字节一致；脚本模拟编辑位置表，再预览/提交回导。
7. 同一设备回到 Room-Z/A01 的 1–2U，名称 `RETURNED-SYNTHETIC`；旧表拒绝，原始输入 Hash 保持。

这是 F1–F5 的**合成 CLI 路径**，F4 仅覆盖进程边界，F5 仅模拟表格编辑。
脚本不执行实际 Agent 新会话或 Excel/WPS，不自动升级这些验收状态。

## 4. 用正式包复跑同一脚本

普通包验收按安装说明使用正式 Release，不临时源码构建来代替分发验收。将下列路径替换为实际包目录
和一个新的绝对证据目录，Python 3.11+ 不必来自源码 `.venv`：

```bash
python3.11 -S "/完整Skill路径/scripts/run.py" --verify
python3.11 -S "/完整Skill路径/scripts/run.py" --bundle-info
python3.11 -S "/完整Skill路径/scripts/run.py" --help
python3.11 "/完整Skill路径/scripts/verify_skill_workflows.py" --runner "/完整Skill路径/scripts/run.py" --output "/绝对路径/新的包证据目录"
```

核对 `--bundle-info` 的版本、来源提交、依赖路径和 `yaml_native_extension`，载荷应来自包内。
`--runner` 使每次 CLI 调用使用 `python -S`。用源码跑出的结果不能填入包验收栏。

## 5. 证据读取、失败处理和记录

成功时，证据目录包含以下文件；它们留在私有目录，不整体提交或粘贴到 PR：

| 文件 | 用途与边界 |
| --- | --- |
| `report.json` | `status: passed`、`scope: scripted-cli-synthetic`、六项检查名称、原始 Hash 和 runner；Agent/Office 字段维持 pending，只说明本次脚本不验证这些层级 |
| `events.json` | 实际 CLI 参数、退出码与 JSON 结果，供追溯每一步；含计划 token，不能直接公开 |
| `original.xlsx` / `working.xlsx` / `project.sqlite` | 原件、最终工作副本和持久项目，可独立读回位置/身份；原件 Hash 应与报告一致 |
| `positions.xlsx` | 曾用于回导的表；其版本在提交后已过期，不能当作最终项目的新导出或重复提交 |
| `runtime/`、请求/计划文件及隐藏辅助状态 | 隔离的恢复备份与运行状态；保留以便复核，不能当普通缓存随手清除 |

成功后确认报告、事件、原件和最终业务状态实际存在；按上面预设值独立只读核对 XLSX XML 或预先确定的
人工核对表，不仅凭同一个 Parser 再读一遍。保留证据后再清理临时进程/工作区，证据不随清理丢弃。
脚本使用短生命周期 CLI，不启动桌面应用或常驻服务。

现有脚本只在整条流程成功结束时写 `report.json` 和 `events.json`。失败时保存退出码、stdout/stderr
到证据目录之外的日志位置，保留已生成文件；缺少报告或部分文件不算 PASS。先核对执行路径和输入状态，
修正原因后用新目录复跑，不覆盖失败证据，不为通过而放宽断言。

每次在 `docs/updates/` 或任务交接记录以下摘要，原始数据和 token 留本地：

```text
日期/时区、操作系统/架构、Python（实际 Agent 验收另记软件与模型）
被测对象：源码提交与工作区状态，或正式包版本/来源提交/ZIP Hash
实际解释器与 Core 路径、输入 Hash、私有证据位置
用户路径 F1–F5、实际命令、预期/实际、PASS/FAIL/PENDING、跳过原因
源码检查 / 正式包 / 实际 Agent / Excel-WPS 各层结果及剩余工作
```

功能或 CLI 变化时，在同一 PR 更新对应行和验证入口，并复跑受影响路径。
区分文档过期、验证工具缺口与产品回归；发现产品回归时记录问题，不能仅修改通过标准掩盖失败。
本页首次实跑见[2026-10-31 记录](../updates/2026-10-31-verification-entry.md)。
