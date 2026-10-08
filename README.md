# AI Tools

这是我自己的小工具仓库。每个工具单独放在 `projects/` 下面，互不影响。

想用哪个，点进对应目录看它自己的 README 即可。GitHub 上的 `main` 是正式版本。

## 里面有什么

| 项目 | 类型 | 做什么 |
| --- | --- | --- |
| [codex-quota-bar](./projects/codex-quota-bar/) | macOS 菜单栏 | 看 Codex 额度还剩多少 |
| [deepseek-harness-radar](./projects/deepseek-harness-radar/) | 观察笔记 | 跟踪 DeepSeek Harness 官方和插件生态 |
| [racktool](./projects/racktool/) | Excel 工具 | 机柜表读取、核对和本地驾驶舱 |
| [wf610-ble](./projects/wf610-ble/) | macOS 菜单栏 | 把 WF610A 蓝牙转成 SecureCRT 用的串口 |

## 仓库怎么摆

```text
.
├── README.md              # 你正在看的这一页
├── AGENTS.md              # 给 Codex / 代码助手看的仓库规则
├── .gitignore
├── .github/workflows/     # 只在对应项目改动时跑的检查
└── projects/
    ├── codex-quota-bar/
    ├── deepseek-harness-radar/
    ├── racktool/
    └── wf610-ble/
```

根目录不放某个工具的源码。新工具一律新建 `projects/<名字>/`，并在这个目录里写 README。

## 以后加新工具

1. 建目录：`mkdir -p projects/my-new-tool`
2. 把源码、脚本、说明都放进这个目录
3. 写一份 `README.md`：做什么、怎么运行/构建、当前状态
4. 回到这一页，把新项目加进上面的表格

`mkdir -p` 的意思是：按路径创建文件夹；中间目录没有就一起建，文件夹已存在也不报错。把 `my-new-tool` 换成实际项目名。

如果某个工具需要 GitHub 自动检查，再在 `.github/workflows/` 加一个只盯这个目录的工作流。

## 给 Agent 的入口

这个仓库由 Agent 日常维护，不依赖人工点 GitHub。

任何新增、修改、提交、开 PR、合并到 `main` 的任务，都先读 [`AGENTS.md`](./AGENTS.md)。默认从最新 `origin/main` 开独立分支，一次只动一个项目，用 PR squash 合进 `main` 后删除临时分支。

不要在 RackTool 或其他功能分支上夹带无关项目。

## 后续开发与维护

1. **提出需求**：在对应项目的会话说明目标；报 Bug 时附应用版本、复现步骤、预期与实际结果。
2. **Agent 开工**：读取最新远端 `main` 和项目文档，建独立分支/工作区；一次 PR 处理一个项目的明确目标。
3. **验证与落库**：完成相应检查，把问题、修复行为、验证结果和未完成项写回项目文档。用户不用重复整理 Git 操作。
4. **交付与归档**：按授权合并 PR、确认 `main` 已更新；代码和重要资料保存后归档已完成会话。后续新问题从当前仓库开始，通常无需回看旧会话。

RackTool 日常在云端开发，保留一个总控入口；桌面与 Excel/WPS 在本地验收。
具体启动、检查、私有数据交接、会话管理和下一阶段顺序见
[RackTool 云端开发流程规范](projects/racktool/docs/development/cloud-workflow.md)。
额度栏和 WF610 是个人维护工具，有新问题时直接按对应 README 开始任务。
它们的 Mac 编译、安装和实机操作仍需本地环境；源码在 GitHub 不等于已安装 App 或运行配置自动更新。

会话归档可能清理 Codex 托管工作区。先核对未推代码和私有备份；不随会话整理删除本地 App、
数据库、运行记录、蓝牙/终端配置或历史工作区。
