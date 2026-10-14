# RackTool Skill 安装与更新

适用版本：独立包 `2026.10.14.1`；安装方式核对日期：2026-10-14。

## 先分清两种包

- 旧的 `RackTool-Skill.zip` 仅含说明，依赖已有 RackTool 仓库和 Python 环境。
- 新的 `RackTool-Skill-2026.10.14.1.zip` 包含 RackCore、CLI、Profile、技能说明、安装器，以及
  openpyxl / et_xmlfile / PyYAML 的固定版本纯 Python 依赖和许可证。安装后不用克隆 AI-Tools，
  不用 pip 安装 RackTool，不需要 GUI/Qt，也不用访问 GitHub 才能解析或编辑 Excel。
- 包不包含 Python 解释器、Agent 软件、业务 Excel、项目 SQLite。电脑需要 Python 3.11+，
  Agent 需要能访问工作目录并执行本地 Python。没有解释器时从
  [Python 官方下载页](https://www.python.org/downloads/)安装。Core 离线运行；
  AI 对话是否联网由所用 Agent 决定。

本轮 ZIP 和 SHA256 作为会话附件提供。源码、此文档和构建脚本保存在
[GitHub 项目主页](https://github.com/Dylanx42/AI-Tools/tree/main/projects/racktool)。
当前未发布 GitHub Release；仓库的“Download ZIP”是源码包，不能替代此独立安装包。

## Codex：推荐完整目录安装

不想操作终端时，下载新版 ZIP 后在本机 Codex 对话中说：

> 把下载目录里的 RackTool-Skill-2026.10.14.1.zip 完整安装为本机 Codex 的 racktool Skill。
> 检查 Python 3.11+；已有同名安装先移出技能目录备份。安装后校验包，报告版本和实际 Core 路径。
> 不更新整个 AI-Tools 仓库，不改业务原图。

Agent 应执行下面的完整目录安装流程，并报告实际工具结果。

解压新版 ZIP 到独立的 `racktool` 文件夹，`SKILL.md` 必须直接位于这个文件夹内。
不要再多嵌套一层。把整个文件夹放到：

- macOS / Linux：`~/.agents/skills/racktool/`
- Windows：用户目录下 `.agents/skills/racktool/`

也可以在解压目录让 Agent 执行 `python install.py --agent codex`。macOS 一般使用 `python3`，
Windows 可使用 `py -3.11` 或已确认版本的 `python`；不要默认 `python` 一定满足版本。
已有同名目录时安装器拒绝覆盖；先移到技能目录以外备份，避免两份同名 Skill 同时加载。

刷新/重启 Codex，发出：

> 使用 $racktool。先核验完整安装包，告诉我包版本、实际加载的 Core 路径和 Python 版本。
> 然后按 LOCAL_ACCEPTANCE.md 在新的验收工作目录测试，不使用旧仓库环境，不改我的原图。

[Codex 官方技能文档](https://learn.chatgpt.com/docs/build-skills)说明用户目录和项目目录的发现规则。
这是本地技能目录安装，不代表已上架 Codex 插件市场，也不是 ChatGPT 网页版上传安装流程。

## WorkBuddy：导入完整 ZIP

打开“技能”→“添加技能”→“上传技能”，选择新版 ZIP，启用 RackTool。
按[WorkBuddy 官方文档](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)
使用本地技能包导入，不用仅上传 SKILL.md。

安装后在对话中说：

> 用 RackTool 技能。先找到技能的实际安装目录，执行 scripts/run.py --verify 和 --bundle-info。
> 检查 core/src/racktool 和 vendor 是否完整；然后按 LOCAL_ACCEPTANCE.md 验收。

若导入器没有保留辅助目录，把完整解压目录放到你允许 Agent 访问的目录，让它读取该目录的
SKILL.md 并运行同目录脚本。记录为“手动目录加载”，不能记作“自动发现安装通过”。
WorkBuddy 的脚本保留、执行授权及实际加载结果必须在该软件内验证。

## TRAE：完整目录优先

中国版 TRAE IDE / TraeWork：将完整 `racktool` 文件夹放入 `~/.trae-cn/skills/`，或在解压目录
执行 `python install.py --agent trae-cn`。Windows 是用户目录下 `.trae-cn/skills/racktool/`。
项目安装可放在 `.trae/skills/racktool/`；用 `--destination` 指定完整目标路径。

[TRAE IDE 官方文档](https://docs.trae.cn/ide_skills)和
[TraeWork 官方文档](https://docs.trae.cn/work_skills)给出了目录规则。
IDE 的 ZIP 导入主要描述提取名称/指令；因此本包推荐复制完整目录，以保留脚本和 Core。
国际版全局路径未在本轮核实，请使用该版官方界面确认，或用项目目录方式测试。
TRAE CLI 的目录另有规则，不要把 IDE 的路径当成 CLI 的路径。

对话开场：

> 用 RackTool 技能，先报告实际技能目录与包版本，核验完整包并按 LOCAL_ACCEPTANCE.md 测试。
> 如果只加载了说明、缺少 Core，请停止并报告安装不完整，不自行编写 Excel 修改逻辑。

## 更新、回滚与卸载

1. 停止当前写入，保留业务原图、工作副本、SQLite 和备份；这些文件放在技能目录之外。
2. 下载新版本并核对附件 SHA256，解压后让 Agent 执行 `scripts/run.py --verify`。
   包内校验用于发现损坏，不是数字签名或来源认证。仅忽略系统生成的
   .DS_Store/Thumbs.db/desktop.ini 和 Python 缓存，其他额外文件仍拒绝。
3. 把旧技能完整目录移出 Agent 技能扫描目录备份，安装新版，刷新后查 `--bundle-info`。
4. 每个平台跑轻量读图/导出回归；有状态格式变更时按新版迁移说明操作，不能直接丢弃 SQLite。
5. 回滚时恢复旧技能目录和对应状态备份；单纯换代码不能保证兼容未来新版数据库格式。
   卸载只移除技能目录，不删除业务工作目录。

## 开发者重建包（使用者无需执行）

从明确 Git 提交的干净仓库，在项目开发环境安装 `bundle-requirements.txt` 的固定版本后：

```bash
python scripts/build_skill_bundle.py --version 2026.10.14.1 --output dist/RackTool-Skill-2026.10.14.1.zip
```

包内 `bundle.json` 记录 Git 提交、是否脏工作区、依赖版本；`checksums.json` 记录所有有效载荷。
发布只使用 `source_dirty=false` 的包。版本号属于 Skill 交付包，不等同 Core 历史 `0.1.0`。
构建只选择 Core/CLI/Profile、技能文件和依赖；真实数据和 GUI 不进入包。
