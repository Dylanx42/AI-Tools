# RackTool 云端开发与本地交接

日常代码、CLI、自动化测试和 Qt widget 开发在云端进行，代码通过 GitHub 分支/PR 保存。
RackTool 本身继续离线可用；云端开发不增加产品云服务或 Agent 运行时依赖。
Microsoft Excel/WPS 和 macOS/Windows 最终桌面验收仍在对应设备执行。

## 当前开发基线（2026-10-08）

正式代码以 `Dylanx42/AI-Tools` 的最新 `origin/main` 为准。新版 GUI、Excel 导出、
受管理的项目存储、Windows 打包及后续解析修复已通过 [PR #7](https://github.com/Dylanx42/AI-Tools/pull/7)
合入主线；其来源 `c925653` 与已确认的 Mac 主工作区源码一致。云端工具适配这套新版，
后续不再在旧主线和新版 GUI 两个工作区之间来回选择。

| 内容 | 位置/状态 |
| --- | --- |
| 主仓库 checkout | `/workspace/AI-Tools`，开工先 fetch；不在混合 checkout 直接提交 main |
| 本轮云端工作区 | `/workspace/racktool-cloud`；任务分支合并后仅作本轮参考 |
| 原新版参考工作区 | `/workspace/racktool-gui-reference`；保留比较，不作为新任务基础 |
| 云端环境 | Linux x86-64，Python 3.12.14，Qt 6.11.2 |
| 本地主工作区 | 历史核对为 `c925653`、无未提交改动；新主线合并后由本地 Agent 再同步 |
| 其他本地工作区 | `codex/racktool-gui-usability` 干净，但 `0fdffc4` 补丁等价性未核对，继续保留 |
| 私有样本 | 14 个原始数据文件，两个 Sheet-scoped Golden 和一份验收记录，Hash 未变 |

整合后的云端检查：`python scripts/dev.py check --gui --require-private`。
本轮 pytest **161 passed、0 skipped**，Ruff / strict mypy / pip check / CLI / 新版 Qt
widget 冒烟通过。私人回归为一个 workbook 的两类 Sheet 布局和 Profile 验证，
不能把测试数量解释成额外真实 workbook。公开 CI 不持有私有数据，相应测试明确跳过。

仓库新增 `RackTool checks`：Linux Python 3.11/3.12，以及 macOS/Windows Python 3.11
运行同一个公开检查入口。既有 Windows package 工作流负责便携打包。
工作流配置已落库不等于托管 runner 已通过；以 GitHub Actions 对应 commit 的实际结果为准。
桌面、Excel/WPS 和 Windows ARM 实机验收继续单独记录。

`docs/racktool-allinluna-policy` 等历史未合并分支不是正式代码或模型策略，本次不合并。
本地 GUI 的 SQLite 业务项目状态未在上传包中，尚未迁移；详见下文。

## 后续开发流程规范

### 用户如何提出任务

在云端总控会话说明“哪个项目、想达到什么结果”。修 Bug 时补充应用版本、操作步骤、
预期/实际结果和截图或文件；已有信息足够时 Agent 自行核对仓库，不要求用户重复整理 Git。
不按模型名（例如 Grok）划分项目，也不把历史聊天当开发文档。

保留一个 `RackTool｜云端总控` 会话用于计划与汇总；需要实机操作时使用一个
`RackTool｜本地验收` 会话。并行功能各用独立任务分支和工作区；Agent 子任务由总控汇总。
一个功能完成即收口，不长期复用旧功能会话做无关改动。
额度栏和 WF610 是个人维护工具，有新问题时按项目另开任务即可。

### Agent 开工、实施、交付

1. **开工**：fetch 最新 main，读根/项目 README 和 AGENTS；查状态、分支、worktree、
   相关 PR 与已知待办。从最新 main 建独立任务分支，先复现再修改。
2. **实施**：一次 PR 只处理一个项目的一个明确目标；解析 Bug 添加最小回归样本；
   变更不越过 RackCore、离线运行及 Excel 安全写回边界。并行 Agent 不同时改同一核心模块。
3. **验证与记录**：运行统一检查，私有数据已安装时加 `--require-private`。
   同步项目修复记录/当前状态，写清问题、最终行为、复现或回归检查、验收结果和未完成项。
   设计变化写 ADR。失败业务详情仅留私有日志。
4. **落地**：只提交预期文件，push、开 PR、审查后按用户授权 squash 合入 main，
   删除已合并的远端任务分支。已发布分支同步新 main 使用普通 merge，禁止未经授权 forcepush。
5. **收口**：fetch 验证 main 包含预期代码和文档；报告 PR、测试、人工待办及干净工作区状态。
   “已同步远端功能分支”和“已合入 main”必须分别说明，不能把前者当作正式交付。

新 Bug 默认读取当前代码、README、修复记录、相关测试及近期 PR；只有存在未落库的决策、
复现材料或验收证据时才回看旧会话。不要求逐一阅读所有历史聊天。

### 归档与清理

归档前确认源码已合入 main，决策和未完成项写入文档，没有独有的未推 commit、脏文件或
未备份私有数据；重要实机证据可在项目记录中摘要，并注明其历史时间和当前未复验状态。
已完成会话优先归档，可恢复；有未交接内容的会话保留并注明待办。

会话归档可能触发 Codex 对托管 worktree 的清理与快照保留，因此不能承诺文件永远不受影响。
不要顺手删除 Mac 历史 worktree、`~/WF610`、已安装 App、运行数据、SQLite 或私有验收附件。
永久删除只用于已经核清且用户明确要求的会话；接口不支持时如实报告已归档或未处理。

### 下一阶段按顺序推进

1. **稳定 V0.5 Beta**：在 Mac、Windows x86-64 的副本上完成打开、总览/机柜/设备操作、
   搜索、移动预览、安全同步、导出、关闭重启和备份恢复；Excel/WPS 检查导出样式与打印。
   Windows ARM 为兼容快测，不能替代 x86-64 验收。把每项结果与待修问题写入 gate。
2. **未知布局工作流**：遵循 ROADMAP/相关 ADR，先做 Analysis Package、候选 Profile、
   validate/dry-run 与置信度确认，保持既有 Golden 不回退。
3. **Skill 和后续编辑能力**：确定性能力先在 RackCore/CLI 验证，再接 GUI 或 Skill。
   Skill 不直接写 Excel，不把 Agent 运行时嵌进本地 App。每次任务再核对路线图，不提前扩大范围。

## 新建云端环境

准备 Git、Python 3.11+ 和 venv；本次固定依赖在 Python 3.12 / Linux 上验证。
保持云端平台提供的代理和 CA 设置。访问 GitHub、PyPI、包下载站需要环境允许对应网络目的地。

```bash
git clone https://github.com/Dylanx42/AI-Tools.git
cd AI-Tools
git fetch origin
git switch -c feat/racktool-my-task origin/main
cd projects/racktool
python scripts/dev.py setup --gui
python scripts/dev.py check --gui
```

`setup` 在项目内创建被 Git 忽略的 `.venv`，editable 安装 RackTool，并用
`cloud-constraints.txt` 固定本次验证的依赖版本。纯核心开发可省略两个命令中的 `--gui`。
不修改系统 Python，也不要求 Docker、Office 或外部数据库。
依赖清单固定运行和开发包版本，不包含离线 wheels、pip 或构建隔离环境的完整锁定。
Python/Qt 版本升级应重新跑全部检查后更新清单；Mac/Windows 兼容性需在对应平台确认。

`check` 依次执行 pip check、pytest、Ruff、strict mypy 和 CLI 启动检查；`--gui` 额外执行
真实 Qt widget 的 offscreen 检查，使用临时 synthetic XLSX 验证 CLI 输出、表格和选择绑定。
运行失败即返回非零状态。缺少真实 Golden 时会明确报告跳过，不记为真实布局验证通过。

日常使用云端解释器：

```bash
.venv/bin/python -m racktool --help
.venv/bin/python -m racktool analyze samples/private/your-workbook.xlsx
.venv/bin/python -m pytest tests/integration/test_safe_sync.py
```

Windows 可用 `.venv\Scripts\python.exe`；`dev.py` 会自动选择系统对应的解释器路径。
云端没有桌面显示器时，普通 `racktool gui` 不能展示窗口；offscreen 只执行自动化。
Linux 云端不能代替 macOS/Windows 原生打包与 Excel/WPS 的人工验收。

## 本地代码交接

先在本地 `AI-Tools` 仓库根目录执行以下只读检查，并把结果提供给当前云端任务：

```bash
git status --short --branch
git log -5 --oneline
git diff --stat HEAD -- projects/racktool
git branch -vv
git worktree list
```

未跟踪源码只显示在 status 中，不能只凭 diff stat 判断本地是否完整同步。
核对本地所在分支、commit、未提交改动和 GUI 版本后，再由本地 Agent 按根 AGENTS.md
只提交 RackTool 的预期代码到独立分支/PR；云端拉取后重新测试。
无法推送时交接相应源码文件和补丁，并保留基础 commit 信息。
不上传 `.git`、`.venv`、应用安装包、登录配置、令牌或其他项目的文件。
不得删除、reset 或 stash 本地改动来让工作区看起来干净。

本次收到的输出确认主工作区干净，HEAD 与其 origin 分支均为 `c925653`，无需交接该工作区的
源码补丁。但输出中的本地 `origin/main` 停留在 `39f6ecb`，不能把该缓存当作 GitHub 最新主线。
分支列表不能证明其他 worktree 干净，也不能证明未跟踪/被忽略的私有文件已同步。

本地补充核对命令：

```bash
git -C /Users/dylan_l/.codex/worktrees/1dff/AI-Tools status --short --branch
git merge-base --is-ancestor 0fdffc4 HEAD
echo "ancestor=$?"
```

最后一项为 0 表示旧 GUI usability commit 已包含在当前新版中；1 表示不包含，其他值表示检查
失败。不包含也不自动意味着缺功能：该分支可能做过 cherry-pick 或改写提交，须比较内容和未提交
改动后再决定交接。`prunable` 是 Git 对旧 worktree 注册的标记，本次不清理或删除本地历史工作区。

用户补充输出确认 GUI usability 工作区干净，ancestor=1。GitHub 无法找到 `0fdffc4`；
当前新版历史中有同名的 `024154f` 提交，但不能只凭标题宣称补丁相同。
当前实际使用的 `c925653` 源码已完整保留在云端；旧分支的独有历史保留在本地，未经核对不删除。

## 私有样本交接

用户已选择将本地 `samples/private/` 迁到云端。交接时保留其完整目录关系：

```text
samples/private/
├── 机柜图-0827.xlsx
├── golden/
│   └── <case>/expected.json
└── <existing analysis and acceptance records>
```

expected JSON 中 workbook 的相对路径、Sheet scope 和 SHA256 必须与原文件一致。
收到文件后先保留原始副本、核对文件清单和 Hash，再放入对应工作区的 Git 忽略目录。
两个工作区测试各自从自己的 `samples/private/` 读取；以校验过的同一份样本分别安装，
不能把某个代码版本写回后的文件当成另一版本的 Golden。

```bash
git check-ignore projects/racktool/samples/private/机柜图-0827.xlsx
# 上一行从仓库根目录执行；下面从 projects/racktool 执行
python scripts/dev.py check --gui --require-private
```

`--require-private` 要求私有 workbook 和至少两个既有 Sheet-scoped Golden case 存在；
具体 Hash、scope、分析结果和 Profile 的正确性由既有回归测试验证。
不要生成或重写 expected 来凑通过。原验收是一个 workbook 中的两类不同布局，
资产清单只是独立对账材料，不能算额外 Golden。
私有源文件、业务内容和验收记录不进入 Git commit、PR、日志或公开测试产物。

本次已接收并安装上传的 ZIP：14 个数据文件、2 个 Golden case 和 1 份验收记录。
Mac ditto 产生的 ZIP 未设置 UTF-8 文件名标志；解包时按原 UTF-8 字节恢复中文文件名，
跳过 `__MACOSX` 等打包元数据。未修改 workbook、expected JSON、分析结果或验收记录。
安装前后、全部测试后均核对全部原始文件 SHA256；两个工作区均通过，且私有文件无 Git 跟踪记录。

原上传包仍保留在云端附件目录，另有项目外的私有解包归档和 Hash 清单；
两个工作区的 `samples/private/cloud-validation/` 保存本次结果和完整测试日志。
失败详情也只保留在私有日志，公开文档/PR 仅记录验证结果，不暴露业务内容。

## SQLite、应用数据与备份

先在本地退出 RackTool，再备份数据库、原始 workbook、Profile 和备份目录，保留本地原件。
历史旧 GUI 默认在工作簿旁保存数据库；当前主线新版 GUI 使用应用数据目录：
macOS `~/Library/Application Support/RackTool`，Windows `%LOCALAPPDATA%/RackTool`，
Linux 的 XDG data 目录。实际位置以本地版本的 storage 实现为准。

迁移开发环境不等于迁移已有业务项目状态。数据库中的 source_workbook 和 Mapping
可能绑定本地绝对路径/Hash，直接复制到云端后不能立即执行 rescan 或 sync。
已有项目需要在交接后单独核对路径绑定、ID 保持和备份恢复；不要手改 SQLite 路径冒充完成。
只读 analyze/inspect 可在样本副本上先执行。重新 project import 会产生新项目身份，
不能替代需要保留原 device_id/rack_id 的迁移。

本次样本包不包含 SQLite 数据库。因此当前完成的是源码、开发依赖与 Golden 验证数据的交接，
不声称已迁移本地 GUI 保存的业务项目状态或原 device_id/rack_id。

## 每个云端任务的收口

遵循根目录和 RackTool 的 AGENTS.md：从最新 `origin/main` 创建任务分支，只改 RackTool，
运行检查，提交预期文件、push、开 PR。用户要求落地时才 squash merge 并删除相应分支。
遇到 GitHub 权限失败如实报告；平台 GitHub Connector 可用时可通过其创建 PR。
不把仅留在云端磁盘的修改叫作已经同步到 GitHub。

云端磁盘保留策略由平台决定。本地原件和私有数据备份应保留到迁移校验结束；Git 忽略文件
不会随 Git clone 恢复，不能把云端工作区当作唯一备份。新云端环境使用 setup 重建依赖。

迁移完成需要：本地未推送源码已核对并交接、目标开发基线已确定、云端检查通过、
私有 Golden 回归通过、需要保留的业务状态已验证可恢复。桌面与 Office/WPS 验收
继续明确标为 MANUAL VALIDATION PENDING，直到实际完成。
