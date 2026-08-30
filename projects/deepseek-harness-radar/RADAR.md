# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-08-30  
> **迁移到 AI-Tools**：2026-08-29

## 状态定义

- 🔥 **P0**：直接影响 Harness / 推理 / Agent Runtime 的关键方向
- 👀 **P1**：值得持续观察，可能影响工作流或生态成熟度
- 🧪 **Candidate**：新发现，先验证持续性与真实价值
- 💤 **Archive**：长期无实质进展、被官方能力取代或价值下降

---

## 🔥 P0｜Harness / 推理机制

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| Anchored Standard / 动态 Tool Schema | 仍是最重要的 DSH 推理优化研究线之一；通过控制模型在不同阶段看到的 Tool Schema 影响 reasoning trajectory | 实验性 | Prefab seeding / tool unlock 可靠性已补；新增已知行为：bare Minimal persona 在身份问题上可能回落到训练先验，出现 identity drift，但一行 identity anchor 可修且不破坏机械 anchor 检查 | 是否做真实任务 trajectory A/B；是否跨模型复现；identity anchor 是否进入 opt-in 配置 |
| dsh-routing-suite | 从 Anchoring 进一步走向“任务分类 → persona/reasoning 路由 → 近距离 Context 注入” | 实验性 | router 与 runtime injection 已合并并通过项目自测 | 正式发布、真实 ablation、是否过拟合 benchmark |
| dsh-mcp-lazy | 把动态 Tool Schema 应用到 MCP：按需暴露具体 MCP 工具，降低常驻 Schema 负担 | 可尝鲜 | 已验证多版 DSH；公开实验显示 Tool Schema token 明显下降 | 0.1.2 alpha 兼容、激活准确率、与 MCP Manager 对比 |
| dsh-context | 已从单 Session Context Inspector 扩展成多 Agent Context / 拓扑可观察层，并开始主动兼容 DSH projection contract 代际变化 | 可日常尝鲜 | 当前 0.38.3；已用双 projection contract 覆盖 0.1.0-rc.7→0.1.2-alpha.1，并修复 alpha 下 `undefined` projection value 导致新 Session 推送失败的问题 | 继续验证 0.1.2 alpha 的 Session/projection 后续变化；是否成为 Anchoring / Router / Agent Teams 的标准观测层 |
| Minimal Harness / byte-stable prompt 类 | 通过少工具、稳定前缀、压缩输出降低 Harness 干扰与 cache 成本 | 实验性 | 已出现 ClawCodex 等 DeepSeek 特化实验；identity drift 说明极简 persona 也存在新的行为边界 | 是否形成稳定 DSH 插件与可复现 benchmark；如何在极简与身份/约束锚定间平衡 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams | Agent Teams 已从纯社区探索进入官方仓库孵化 | 官方实验性 | 官方仓库有 experimental Agent Team / tool-agent-team；0.1.2 alpha 已开始大幅调整 Session / persistence / tool presentation 周边 | 0.1.2 alpha 下的兼容、任务模型、通信、恢复、何时正式发布 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + 直接通信方案；已开始补执行前治理 | 可尝鲜 | 0.1.14 完成 staged plan review：先审 roster/DAG，再 Approve & Run | 0.1.2 alpha 兼容、复杂任务稳定性、资源成本、与官方实现差异 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调 | 实验性 | 社区持续出现 conductor / team / workflow 方向 | 状态管理、故障恢复、是否和官方 Teams 合流 |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run / meta-review / 自动停止思路 | 自动停止可靠性、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH 0.1.2 alpha | 官方主线重新高速演进；底层结构变化已进入插件兼容验证期，但 alpha.1 当前仍是 GitHub tag/source 状态而非 npm 可安装发布 | **Alpha** | 2026-08-27 `dsh-v0.1.2-alpha.1` tag；PTC mode、Session known-event fail-closed、ApiProxy transport 移除；截至 2026-08-30 官方主仓无更新提交，npm `latest/next` 仍停在 0.1.1-rc.2 | 第三方 durable event 正式注册/迁移机制；SESSION_FORMAT_VERSION；alpha 后续 tag 是否真正进入 npm 发布通道 |
| 官方 DeepSeek Provider | 官方持续把 Provider、多模态、附件能力收进主干 | Alpha / RC 过渡 | 0.1.1 统一 Vision / Attachment / Files API；0.1.2 alpha 进入更大范围底层重构 | 跨 Gateway thinking、Vision 稳定化、alpha 兼容 |
| Codex / ChatGPT OAuth Provider | DSH 直接使用 Codex / ChatGPT 模型通道 | 早期实验 | 社区已出现 dsh-codex-connect 类产品化尝试 | 0.1.2 alpha 兼容、OAuth 稳定性、模型目录、与 pi-ai 能力边界 |
| 多模型 Router | 根据任务复杂度切模型 / Provider | 早期实验 | 已出现 tier-router / routing-suite 等方向 | fallback、成本/质量数据、真实自动路由价值 |

## 👀 P1｜插件基础设施

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 已从“插件商店”进入插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 修复“pnpm add 已替换包内容但返回失败”时旧版只恢复 manifest、导致被拒绝的新版本仍实际运行的问题；现在精确恢复旧版本/commit 并回读验证；同时恢复对 DSH alpha 的 real-host E2E | 0.1.2 alpha 实际兼容矩阵；Public Update API 稳定化；签名/供应链；失败恢复是否覆盖更多包管理边界 |
| Compatibility / upstream-radar | 专门检测 DSH 上游升级导致插件失效 | 实验性 | 0.1.2 alpha 的 Session/API 变更让这条线重要性进一步上升 | 是否形成 0.1.1→0.1.2 的真实 plugin compatibility matrix；与 Market 集成 |
| Doctor / Plugin Clinic | 插件故障诊断与恢复 | 可尝鲜 | 已出现把插件启动失败摘要送回 DSH Session 做辅助排障的闭环 | 0.1.2 alpha 兼容、自动修复边界、版本冲突诊断、与 Market 整合 |
| Index / Profile / Distribution | 把 Harness + Plugins 组合成 Agent Profile / Distribution | 早期 | 社区开始形成统一索引、Profile、发行版路线 | 版本固定、升级/回滚、组合兼容性，尤其跨 0.1.2 alpha |
| oh-my-dsh | 尝试做 DSH 的“发行版层” | 很早期 | 能力发现、审批、Eval、版本固定、SHA 校验、回滚等方向 | 是否持续维护；能否真正降低而非增加复杂度 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | 尝试复用 Claude Code 的 skills / commands / rules / agents / hooks / MCP 等资产 | 很早期 | 已进入 DSH 插件发现生态 | 0.1.2 alpha 兼容、语义差异、版本漂移 |
| BrowserSkill | 复用已有浏览器登录态并提供 browser tools / 人工接管 | 可尝鲜 | 已进入 DSH 生态并关注 record-safe observation | 权限、安全、浏览器版本兼容 |
| SSH / Remote / Ops | DSH 从 Coding Agent 向更通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | SSH、SFTP、port-forward、remote control 等能力持续出现 | 凭证、安全、审计、最小权限 |
| Memory / Soul | 跨 Workspace Memory、身份与检索注入 | 实验性 | 已出现 token budget、RRF、压缩、防 context explosion 等 | 误记、污染、跨项目泄露、长期成本 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | 已从 UI 插件变成 Web 工作台基础设施 | 可日常尝鲜 | Side Chat、Pinned Terminal、Terminal park、Git/File/Subagent、第三方页面注册 | 0.1.2 alpha 兼容；Session branching 与多工作区工作流 |
| dsh-TUI | 当前较成熟的 DSH TUI 路线，正从独立客户端继续向“可承载第三方插件的前端 Runtime”演进 | 可日常尝鲜 | 新增公开 `./api` / `./test-utils`、`ctx.tuiToast`、动态 permission preset registry 与 runtime theme plugin；同时保留 Session 生命周期与供应链安全保护 | 这些插件接缝的稳定性分级是否兑现；0.1.2 alpha 兼容；多 Agent/第三方插件长期运行边界 |
| dsh-web-ui | Remote / Git / SSH / Doctor / Task UI 综合增强 | 可尝鲜 | Remote 配对、model catalog、Recovery、Doctor 持续增强 | 0.1.2 alpha 兼容、复杂度、安全 |
| Desktop wrappers | 把官方 Harness / Web 做成桌面入口 | 可尝鲜 | 已出现签名/公证、Provider onboarding、Session/Profile | 0.1.2 alpha 兼容；官方是否推出原生 Desktop |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS origin、配对、证书 pinning、LAN discovery | 0.1.2 alpha 兼容、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | 新的长会话 Context reclamation / durable working-state 路线：把“保存状态”和“证明旧 Context 已安全可回收”分成两个状态转换；已有 2026-08-28 机器可读 qualification 与跨 fresh-chat 恢复证据 | 很新；要验证与官方 compaction/session persistence 的边界、非 Git workspace 隔离问题、0.1.2 alpha 兼容 |
| dsh-plugin-hub / dsh-mcp-manager | 项目级/全局 MCP 管理，并可把 Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` 两个原子工具 | 继续对比与 dsh-mcp-lazy 的兼容性、安全边界与 Context 成本 |
| dsh-auto-maintenance | 插件变更自检、状态快照、失败回滚、连续启动失败 rescue | 自动回滚权限重；重点看误回滚、跨平台、与 Market/Doctor 是否重叠 |

---

## 官方 DSH 近期里程碑

| 时间 | 版本 / 变化 | 观察意义 |
|---|---|---|
| 2026-08-13 | 0.1.0 RC 系列快速公开 | npm family / plugin 生态开始明显加速 |
| 2026-08-19 | 0.1.0-rc.8 | 官方 experimental Agent Teams；reasoning_content 相关修复 |
| 2026-08-21 | 0.1.1-rc.1 / rc.2 | Vision、Attachment、Files API 向统一 Harness 管线发展 |
| 2026-08-27 | **0.1.2-alpha.1** | 官方进入新一轮底层重构：PTC mode、Session known-event fail-closed、ApiProxy transport 移除；第三方插件兼容重新成为核心问题；当前为 GitHub tag/source，尚未进入 npm 发布通道 |
| 当前 | Session format / plugin event surface | durable custom event 缺正式注册/迁移面；社区继续提出 external event producer / per-subagent cwd 等 extension contract 需求，但尚未被上游正式采纳 |

## 当前最值得长期盯的对象

1. **官方 0.1.2 alpha 的 Session / persistence / plugin compatibility**
2. Anchored Standard / 动态 Tool Schema + identity drift 边界
3. dsh-routing-suite + dsh-context
4. dsh-mcp-lazy vs dsh-mcp-manager
5. 官方 Agent Teams vs dsh-agent-teams
6. dsh-market + Compatibility + Doctor / Auto Maintenance
7. Claude Code / Codex 生态兼容与 Provider
8. dsh-durable-context / 长会话 Context reclamation

## 当前趋势判断

DSH 生态已经明显分成五层：**模型表现层 → Agent Runtime → Provider → 插件平台 → 产品工作流**。

当前最值得注意的是四条收敛趋势：

- Harness 从固定工具集转向 **动态 Tool Schema / 动态 Context / 动态 reasoning 路由**；
- 多 Agent 从“能并行跑”转向 **执行前计划审查、路由治理与拓扑可观察性**；
- 插件生态从“能安装”转向 **更新 API、兼容性、诊断、自愈、精确回滚与供应链安全**；
- 官方 `0.1.2-alpha.1` 已重新打开 **Session persistence / plugin ABI 兼容** 这一核心问题，而社区工具开始主动为 alpha 建立跨版本适配和真实宿主 E2E。

---

## 维护规则

- `RADAR.md` **只维护当前状态**，不堆每日流水账。
- 每次观察结果写入当月 `history/YYYY-MM.md`，按 `## YYYY-MM-DD｜Delta` 记录。
- 同一个项目只有发生实质变化才再次进入日报。
- 新项目先进入 🧪 Candidate；持续有真实进展后再升 P1/P0。
- 长期无进展、被官方吸收/取代的项目降到 💤 Archive。
- 每日判断都先以本文件 + 最近 7–14 天 history 为历史基线，再做 GitHub 增量搜索。
- 每月最后一次运行或跨月第一次运行时，在当月 history 增加 `月度总结`，并重新审视 P0/P1/Candidate/Archive。