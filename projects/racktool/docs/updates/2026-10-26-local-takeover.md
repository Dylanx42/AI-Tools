# 2026-10-26：本地主开发接管与源码基线

按照 [本地优先开发规范](../development/local-first-workflow.md)，本轮完成本机状态审计、
独立源码环境和首次自动化基线。任务负责人为本地 Agent，云端按明确文件范围接受委派。
本轮不修改产品代码，不发布新包，也不替换已安装的固定版本 Skill。

## 接管与工作区

- 开始时远端 `main` 为 `febaae629bcf907dbc7d9aa39cc42cee5063c772`（PR #27）。
- 原本地主目录位于 `codex/main-sync-20261013` / `6e3ce79`，工作树干净，落后该主线 7 个提交。
  保留原目录与私有状态，不 reset、stash 或覆盖。
- 另一个现存 GUI 工作区位于 `codex/racktool-gui-usability` / `0fdffc4`，工作树干净；
  与主线有 3 个未被其包含的本地提交，保留待单独核对。未把历史 GUI 工作合入本轮任务。
- 其他缺失工作目录的 Git worktree 注册项保留，不 prune、不删除历史分支。
- 新建独立 `racktool-local-takeover` 工作区，从上述主线创建
  `docs/racktool-local-takeover-20261026`，仅记录此次接管与验收结果。
- 本地聊天已命名为“RackTool｜本地主开发”，既有云端入口改名为“RackTool｜云端协作”。
  没有另建聊天、发送云端实现任务或归档旧工作区。

每个新功能或修复仍从最新 `origin/main` 创建单独分支，当前记录分支不承接无关功能。
旧分支的未推提交是否已经由其他提交覆盖，需要独立核对，不能据此批量删除。

## 本次环境与实测

平台：macOS 27.2 / arm64，Python 3.11.9；日期为 2026-10-26（北京时间）。
执行 `python3 scripts/dev.py setup` 创建当前工作区自己的 `.venv`，使用仓库约束安装开发依赖。
本轮不涉及 GUI，未安装 Qt。

已核对解释器为当前工作区的 `projects/racktool/.venv/bin/python`，
`racktool.__file__` 为同一工作区的 `projects/racktool/src/racktool/__init__.py`。
所有源码验证均使用该解释器的 `-m racktool`，未调用全局固定版 Skill 的 runner。

| 检查 | 本次结果 |
| --- | --- |
| `scripts/dev.py check --require-private` | PASS；包括 pip check、pytest、Ruff、strict mypy 和 CLI help |
| pytest | **598 passed、3 skipped、1 warning**，180.78 秒 |
| 两个真实 Sheet Golden 与私有 Profile 回归 | 3 项通过，包含在上述总数中，不重复累加 |
| Ruff | PASS |
| strict mypy | PASS，46 个源文件 |
| `scripts/verify_skill_workflows.py` | PASS，6 组检查；独立 CLI 进程、合成双机房 |

3 个 skip 分别是未安装 PySide6 的 GUI 测试模块（1 个收集级 skip），以及未安装另一份
私有混合方向机柜原图的导出检查（2 个）。不能将其写成“全平台、全部真实图已验收”。
warning 来自已有不支持 worksheet 扩展的拒绝测试。

现有工作流自检覆盖布局检查/规则导入、双方向查询和空闲 U、歧义拒绝、预览不写入、
错误 token 拒绝、跨房改高后身份保持、重放/占用拒绝，以及位置表回导和过期表拒绝。
这些是脚本协议证据，不等于真实 Agent 软件发现技能或 Office 保存验收。

## 实际 Agent 与真实副本

本地 Codex 本轮读取仓库 Skill 与命令说明，实际通过源码 CLI 对已有真实图副本执行
`layout inspect`、项目导入、设备/机柜/空闲 U 查询，以及原版面和标准版面导出。
本次识别结果为 2 个机房 Sheet、90 柜、710 个设备；这只描述该既有 Golden，
不构成新增真实格式兼容性证据。布局 inspect 返回 `review_required`，未强制通过其建议规则。

同一副本上的跨房改高预览和仅改名的 conversation edit 预览均被拒绝：
`unsupported-workbook-object: Resizing/cross-Sheet edits cannot safely preserve these workbook objects`。
每次拒绝后工作副本与 SQLite 的 SHA256 均不变，没有调用提交、删除保护对象或绕过预检。
该原图的成功编辑闭环仍未通过，拒绝结果不能包装成编辑验收成功。

真实图原件和旧状态保持原样。现有 15 份私有材料复制到新工作区用于回归，逐份 Hash 核对；
原目录材料的结束 Hash 与开始一致。旧工作区及其 SQLite 保留。计划、SQLite、日志、
Hash 清单、导出与恢复状态全部保存在本机 Git 忽略目录，不进入此 PR。

## 待完成与交接

用户在本轮明确“先不管”真实图补充，因此暂停索取当前业务图，并暂缓实际 Excel/WPS 验收。
WPS 仅到文件打开对话框后退出，未完成打开、保存、外观、打印或隐藏元数据检查。
Microsoft Excel、WorkBuddy、TRAE 及新聊天恢复也未在本轮验收。

后续按以下边界继续：

1. 用户提供或指定当前真实图后，仅操作副本，重跑实际 Agent 编辑及同一 SQLite 恢复；
   当前保护拒绝应作为单独调查项，不默认取消保护或开始新功能。
2. 从当前 SQLite 新导出，在 Excel/WPS 实际保存位置表后进行 preview/apply；
   分别记录隐藏 ID/元数据、U 方向、版面与打印结果。
3. 涉及成品更新时另走不可变 Release 发布和独立包验收，源码 PASS 不代表固定版 Skill 已更新。
4. 云端协作前提供已推送分支、精确提交、PR、允许修改文件和本表中的未完成项；
   本地私有图、密钥、SQLite 和运行日志不自动上传。

本轮交付是接管/基线记录 PR；是否已合并以 GitHub PR 实时状态为准，未自动合并。
