# AI Tools

个人 AI 小工具、自动化与长期观察项目集合。

这个仓库采用 **一个项目一个自包含目录** 的方式维护。以后新增工具时，统一放到 `projects/<project-slug>/`，不要再把项目源码、构建脚本或项目文档散落在仓库根目录。

## 当前项目

| 项目 | 类型 | 说明 |
| --- | --- | --- |
| [`codex-quota-bar`](./projects/codex-quota-bar/) | macOS 小工具 | 原生菜单栏 Codex 额度查看器 |
| [`deepseek-harness-radar`](./projects/deepseek-harness-radar/) | ChatGPT 自动化 / Radar | DSH 官方与插件生态的每日观察、当前判断与历史 Delta |
| [`RackTool`](./projects/racktool/) | 跨平台工具（V0.5 automated PASS） | Excel 机柜管理工具；RackCore + GuiSession/headless 已通过，Excel/WPS 与 macOS/Windows GUI 实机验证待完成 |

## 仓库结构

```text
.
├── AGENTS.md
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       └── codex-quota-bar.yml
└── projects/
    ├── codex-quota-bar/
    │   ├── README.md
    │   ├── Sources/
    │   ├── Info.plist
    │   ├── build.sh
    │   ├── CHANGELOG.md
    │   ├── PRIVACY.md
    │   └── SECURITY.md
    ├── deepseek-harness-radar/
    │   ├── README.md
    │   ├── RADAR.md
    │   └── history/
    └── racktool/
        ├── AGENTS.md
        ├── README.md
        ├── README_PHASE0.md
        ├── pyproject.toml
        ├── docs/
        ├── samples/
        ├── src/
        └── tests/
```

## 维护约定

- 每个工具、自动化或长期观察项目都必须拥有独立目录：`projects/<project-slug>/`。
- 项目自身的源码、脚本、配置、README、CHANGELOG 等都留在项目目录内。
- 仓库根目录只保留仓库级文件，例如 `README.md`、`AGENTS.md`、`.gitignore` 和 `.github/`。
- 新项目至少提供一个 `README.md`，说明用途、依赖、运行/构建方式和当前状态；仅文档落库的 Phase 0 项目可暂用 `README_PHASE0.md`，并在首个开发任务中创建正式 `README.md`。
- 公共 CI 放在 `.github/workflows/`，并使用 `paths` 限制只在对应项目变化时触发。
- 构建产物、缓存和本地临时文件不要提交。

## 新增项目

推荐流程：

```sh
mkdir -p projects/my-new-tool
```

然后把该项目的全部文件放进这个目录，并补齐 `README.md`。如果需要 GitHub Actions，再在 `.github/workflows/` 新建与项目同名的工作流。

给 Codex 或其他代码 Agent 下任务前，优先让它先阅读根目录 [`AGENTS.md`](./AGENTS.md)。
