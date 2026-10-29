# RackTool 本地验收规范

从 2026-10-14 起，验收对象改为“固定版本独立 Skill 包 + Agent 对话 + Excel/WPS 输出”。
普通安装和成品验收无需拉取整个 GitHub 仓库，不再要求 GUI 排序、缩放或窗口操作通过。
开发分工自 2026-10-26 起为**本地主开发、云端协作**：本地负责源码实现、调试、回归和实际 Agent
调用；云端只接明确委派的任务；GitHub Actions 执行跨平台检查和正式包构建。Excel/WPS 人工
验收按用户授权在实际机器进行。源码开发仍需要 checkout 和独立 .venv，不能用固定版 Skill
代替验证新代码。详见[本地优先规范](https://github.com/Dylanx42/AI-Tools/blob/main/projects/racktool/docs/development/local-first-workflow.md)。

2026-10-30 状态：本机 Codex 明确调用 `2026.10.28.1` 和独立新会话恢复的**合成验收通过**，
见[验收记录](https://github.com/Dylanx42/AI-Tools/blob/main/projects/racktool/docs/updates/2026-10-30-agent-recovery-acceptance.md)。
真实图、Windows 实机和 Excel/WPS 继续暂缓；其他 Agent、自动发现和真实格式兼容性不在该结论内。
下列内容是完整验收规范，不表示要求本轮恢复暂缓项目；合成结果也不能将第三层标记为 PASS。

## 工作目录和证据

建立独立 `RackTool验收/<包版本>/<agent>/`，各 Agent 用相同输入原图的独立工作副本：

```text
inputs/     原始 Excel，只读留存
working/    编辑副本
projects/   SQLite 稳定身份与状态
outputs/    原版面/标准版面导出
logs/       安装版本、命令结果、问题和人工核对记录
```

这个目录不放在技能安装目录中。验收时可为进程设置 RACKTOOL_DATA_DIR 为该 Agent 验收目录
中的 backups，以隔离并定位恢复文件；未设置时 Core 使用操作系统应用数据目录。
不得把真实文件和设备名称提交到公共仓库。
每个 Agent 的证据记录：操作系统/架构、Agent 版本、包版本/Git 提交、Python 版本、输入 SHA256、
实际 Core 路径、操作、预期/实际、PASS/FAIL/PENDING、输出路径。原图操作前后 SHA256 必须相同。
云端测试通过不是“Codex/WorkBuddy/TRAE 在你的电脑验收通过”。

## 第一层：安装和独立运行

请 Agent 找到技能目录并用本机 Python 3.11+ 运行：

- `scripts/run.py --verify`：完整载荷校验成功。
- `scripts/run.py --bundle-info`：版本正确，Core 来自此包，openpyxl/yaml 来自 vendor，PyYAML
  不使用平台二进制扩展；没有引用旧仓库或虚拟环境里的 RackTool。
- `scripts/run.py --help`：无需 pip/仓库/Qt 仍可运行。

一次普通 Python 成功后，可让 Agent 用 `python -S scripts/run.py --bundle-info` 验证不依赖
site-packages。若 Agent 限制执行脚本，记录阻塞，不把“能读 SKILL.md”当作安装验收通过。

## 第二层：自然语言调用

在每个软件内新开会话，明确“使用 RackTool”，依次测试：

| 场景 | 对话示例 | 通过标准 |
| --- | --- | --- |
| 读图 | 看这份机柜图，汇总机房、机柜、设备和 U 方向 | 实际运行 Core，原图不变，不凭截图猜方向 |
| 空图 | 创建 A01–A18、B01–B18，42U，设备位单格 | 36 柜、每柜 42U，Excel 可打开 |
| 新增 | 在指定机房机柜的空闲连续 2U 添加测试设备 | 唯一定位，先预览、校验，再写工作副本 |
| 仅预览 | 把测试设备移到另一个空位，先看看 | 输出计划但副本/SQLite 不变 |
| 落实 | 落实刚才的移动并改名，再导出 | 已明确授权时执行，稳定 ID 不变，重扫一致 |
| 拒绝 | 移到已占用位置或柜外 U 位 | Core 拒绝，文件与数据库不变，不绕过校验 |
| 歧义 | 只说 A01，文件有两个机房同名柜 | 问清机房，不猜选对象 |
| 恢复 | 关闭会话重新打开，从已有项目继续查询 | 读取原 SQLite，身份/位置保持，不重新 import 丢状态 |
| 限制 | 移到过窄设备区或互占源区域的批量换位 | Core 拒绝，不自行写 Excel |

不得让 Agent 为业务变更临时写 openpyxl、SQL 或替代 Parser。不得把“AI 说已完成”当成执行证据。
一次完整验收后，小版本更新在各软件做安装校验、真实图读图、原版面导出和一次副本编辑即可；
涉及解析/写回/数据库变化再扩展相关场景。

## 第三层：实际 Excel/WPS

以你提供的真实图为首轮样本，让 Agent 同时交付原版面和标准版面两份 Excel。
独立核对表不要完全由被测 Parser 自己生成；至少抽查两种 U 方向、一个 2U 设备和编辑对象。

- 原版面：各机房 Sheet 名、位置、U 从上往下/从下往上、合并、文字、颜色、宽高和打印版式
  与工作副本相符；原有无关 Sheet 留存。无修复警告，打印预览可用。
- 标准版面：每机房独立 Sheet，各机柜保留自己的 U 方向；每 U 一个设备格，多 U 纵向合并。
- 设备位置表：第 1 行就是筛选标题；没有顶部三行注释和来源坐标；机房取原 Sheet 名；
  U 位单列显示 `21-22U`/`21U`；内部 ID 隐藏。设备文字多行、行高、筛选和实际位置对应。
- 编辑后再次打开文件和已有 SQLite，新增/改名/移动准确，冲突拒绝后未留下部分写入。
  原始上传文件 Hash 不变；副本和恢复备份可找回。

文件能被 Core 重开只构成自动化验证，不能代替这一步。

## 成品使用与源码开发的更新流程

本地主导修复（云端按委派协作）→ GitHub PR/文档/回归 → GitHub Actions 发布正式 Skill ZIP →
本机从 Release 更新 Skill → 按变更范围验收 →
反馈包版本、Agent/系统、复现请求和输出问题。查历史优先读仓库当前记录；仅缺少证据才回看旧会话。
日常使用者无需同步源码；承担源码开发的本地 Agent 需从最新主线准备独立工作区。
已安装 Skill 是固定版本，不会跟着 main 或仓库文档自动更新。

普通本地安装不执行源码构建；无法下载完整发布包时记录安装阻塞，不用现场构建掩盖分发失败。

## 本轮新增验收（2026-10-15）

- 对话：按机房/柜名/文字/U 定位，查询 free，preview 后核对 Hash 不变，apply 同一 token，
  重启会话继续 query。错 token、改过的计划、过期项目/源及重放都应拒绝。
- 布局：inspect → 核对 Sheet/方向/候选 → propose → check → 按报告 SHA 导入；
  低置信停在 review，不能强制猜。不同 Profile 的机房暂分别建项目。
- 绑定编辑：在同一项目绑定的同一工作簿内，同机房与跨机房各做一次改高/移动，核对多行文字、
  U 映射、合并/样式和稳定身份。普通 move 保持高度；改高使用 edit。占用、越界、目标过窄和
  不能安全保留的对象必须拒绝，不要求受保护样本强行移动；不测试跨工作簿/跨项目迁移。
- 表格回导：从当前项目重新导出，B设备/C机柜/D U位/E高度/F机房可编辑；范围与高度一致。
  使用整张表排序、保留 H/I 隐藏 ID 和隐藏名字元数据，再 preview/apply。检查整批变化和备份。
  旧导出、删/增行、改状态、改隐藏 ID、重复 ID、公式、旧 token 均须拒绝。
- 元数据在 Excel/WPS 保存后是否保留需分别验证；被删除时应报告重新导出，不能按行号猜 ID。

自动化自检（由本机 Agent 执行，合成测试不修改你的真实原图）：
`python /完整Skill路径/scripts/verify_skill_workflows.py --runner /完整Skill路径/scripts/run.py --output /新的验收证据目录`。
脚本已随完整包交付，不需拉取源码；它不代表本机 Agent 的自然语言调用已通过。
