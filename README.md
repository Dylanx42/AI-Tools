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

给 Codex 下任务前，让它先读 [`AGENTS.md`](./AGENTS.md)。
