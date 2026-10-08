# RackTool 云端开发与本地交接

日常代码、CLI、自动化测试和 Qt widget 开发在云端进行，代码通过 GitHub 分支/PR 保存。
RackTool 本身继续离线可用；云端开发不增加产品云服务或 Agent 运行时依赖。
Microsoft Excel/WPS 和 macOS/Windows 最终桌面验收仍在对应设备执行。

## 当前迁移基线（2026-10-08）

| 内容 | 云端位置/状态 |
| --- | --- |
| 正式仓库 | `Dylanx42/AI-Tools`，`origin/main` |
| 迁移开发工作区 | `/workspace/racktool-cloud`，`feat/racktool-cloud-workflow` |
| 已拉取主线 | `037f05a590cf585eff2e3ba0a9c7325e0f17c3e3` |
| 新版 GUI 参考工作区 | `/workspace/racktool-gui-reference`，detached `c925653858683f2cebcd8060749f2990afe3141a` |
| 新版来源 | `fix/racktool-gui-redesign`，[PR #7](https://github.com/Dylanx42/AI-Tools/pull/7)，尚未合并 |
| 运行环境 | Linux x86-64，Python 3.12.14 |
| 本地未推送代码 | 用户确认存在，等待本地状态和文件交接 |
| 私有 Golden 数据 | 用户准备迁入云端，当前尚未提供 |

新版 GUI 包含页面重设计、Excel 导出、Windows 打包和后续解析修复。
另有 `codex/racktool-gui-redesign` 旧版和 `docs/racktool-allinluna-policy` 未合并分支；
这些分支不是正式主线。本次不替用户选择本地版本，不合并旧 PR，也不改变其模型策略。
参考工作区用于比较；需要开发该版本时从最新主线建立独立分支，再审查/整合指定成果。
不要在 detached 工作区直接开始提交。

本次云端复跑结果（两个工作区分别拥有自己的 `.venv`，使用同一依赖清单）：

| 基线 | pytest | Ruff / strict mypy / pip check / CLI |
| --- | --- | --- |
| 主线 + 本次迁移工具 | 109 passed, 2 skipped | PASS；另有 Qt widget + deterministic CLI smoke PASS |
| 新版 GUI 参考 commit | 158 passed, 2 skipped | PASS；pytest 包含 Qt offscreen widget 测试 |

两项跳过均源于 Golden 数据尚未安装。这些结果不是原私有验收 112/159 passed 的重新证明。
主线的 `check --require-private` 在缺少样本时已验证返回失败，不会静默放行。
Qt 安装后主线旧的静态导入 ignore 会触发 mypy unused-ignore；本次改成延迟模块加载，
保留 GUI 为可选依赖，并已复跑全部检查。

新版参考环境的复跑命令（从其 `projects/racktool` 执行）：

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -ra
.venv/bin/python -m ruff check .
.venv/bin/python -m mypy src
.venv/bin/python -m pip check
```

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

## SQLite、应用数据与备份

先在本地退出 RackTool，再备份数据库、原始 workbook、Profile 和备份目录，保留本地原件。
主线旧 GUI 默认在工作簿旁保存数据库；新版 GUI 使用应用数据目录：
macOS `~/Library/Application Support/RackTool`，Windows `%LOCALAPPDATA%/RackTool`，
Linux 的 XDG data 目录。实际位置以本地版本的 storage 实现为准。

迁移开发环境不等于迁移已有业务项目状态。数据库中的 source_workbook 和 Mapping
可能绑定本地绝对路径/Hash，直接复制到云端后不能立即执行 rescan 或 sync。
已有项目需要在交接后单独核对路径绑定、ID 保持和备份恢复；不要手改 SQLite 路径冒充完成。
只读 analyze/inspect 可在样本副本上先执行。重新 project import 会产生新项目身份，
不能替代需要保留原 device_id/rack_id 的迁移。

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
