# RackTool Phase 0 Documentation Pack

本目录是 RackTool 开工前置文档包。

> 历史说明：本文件记录 Phase 0 启动流程，不代表当前项目状态。当前入口与验收状态见
> `README.md` 和 `docs/gates/V0.5-integrated-audit.md`。

## Phase 0 当时推荐使用流程

本包现在按“**本地 Codex 先落库 → GitHub 远端仓库 → Codex Cloud 正式开发**”的方式使用：

1. 把整个 `RackTool-Phase0-Docs.zip` 交给本地 Codex。
2. 让本地 Codex 按 `docs/research/codex-local-bootstrap-prompt.md` 执行：
   - 找到你本地已有的 `AI-Tools` Git 仓库；
   - 将本包中的 `RackTool/` 合并到仓库根目录下的 `projects/racktool/`；
   - 检查 Git 边界与文件完整性；
   - 提交并 push 到远端仓库。
3. 确认 GitHub 远端已经出现 `AI-Tools/projects/racktool/` 及本包文档。
4. 再进入 Codex Cloud，选择 `AI-Tools` 仓库，并使用 `docs/research/codex-cloud-kickoff-prompt.md` 开始 V0.1 Reader 开发。

> 本包本身不需要在交给本地 Codex 前手工拆文件、改路径或逐个上传。

## 建议阅读顺序

1. `AGENTS.md`
2. `docs/product/requirements.md`
3. `docs/research/background-research.md`
4. `docs/architecture/overview.md`
5. `docs/architecture/data-model.md`
6. `docs/architecture/profile-design.md`
7. `docs/roadmap/ROADMAP.md`
8. `docs/decisions/README.md`
9. `docs/research/codex-local-bootstrap-prompt.md`
10. `docs/research/codex-cloud-kickoff-prompt.md`

## Phase 0 当时待补充（现已完成）

Phase 0 当时尚无真实 Golden Sample `.xlsx`。此缺口现已由一个真实私有机柜 workbook 内的两类
Sheet-scoped Golden 布局补齐；资产清单不是第二个机柜 Golden。私有材料仍保持 Git 忽略，
synthetic workbook 也始终不得冒充真实 Golden 或替代真实格式兼容性证据。
