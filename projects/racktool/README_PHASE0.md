# RackTool Phase 0 Documentation Pack

本目录是 RackTool 开工前置文档包。

## 当前推荐使用流程

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

## 当前仍待补充

真实 Golden Sample `.xlsx` 仍需后续补充。第一轮开发只允许使用 synthetic workbook 建立 Reader 与测试框架，不得根据截图猜测真实 Excel 结构。
