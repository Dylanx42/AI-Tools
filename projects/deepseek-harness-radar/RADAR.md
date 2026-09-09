# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-09-09  
> **迁移到 AI-Tools**：2026-08-29

## 状态定义

- 🔥 **P0**：直接影响 Harness / 推理 / Agent Runtime 的关键方向
- 👀 **P1**：值得持续观察，可能影响工作流或生态成熟度
- 🧪 **Candidate**：新发现，先验证持续性与真实价值
- 💤 **Archive**：长期无实质进展、被官方能力取代或价值下降

## 🔥 P0｜Harness / 推理机制

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| Anchored Standard / 动态 Tool Schema | 仍是最重要的 DSH 推理优化研究线之一；通过控制不同阶段可见 Tool Schema 影响 reasoning trajectory | 实验性 | Prefab seeding / tool unlock 已补；Minimal persona 已确认 identity drift 边界 | 真实任务 trajectory A/B、跨模型复现、identity anchor |
| dsh-routing-suite | 任务分类 → persona/reasoning 路由 → 近距离 Context 注入；官方开始提供“动态修改 system prompt 且不破坏 KV Cache”的模型能力面后，这条线与官方 Runtime 的交叉价值上升 | 实验性 | `0.1.5-alpha.1` 新增 opt-in dynamic system-prompt update without KV-cache invalidation | 哪些模型声明支持；动态 prompt 对 cache hit / trajectory / persona 边界的真实 A/B；routing-suite 是否复用官方能力 |
| dsh-mcp-lazy | MCP 工具按需暴露，降低常驻 Schema | 可尝鲜 | 多版 DSH 已有验证 | **0.1.5-alpha.1** 兼容、激活准确率、与 MCP Manager 对比；MCP `tools/list` 异常分页的超时/上限保护 |
| dsh-context | 多 Agent Context / 拓扑可观察层；已开始主动跨三代 Session log 做 shape-driven 兼容 | 可日常尝鲜 | `dsh-context@0.46.1` 已验证 `0.1.2-rc.1` V0、`0.1.3-alpha.2` V2、`0.1.5-alpha.1` V3，并在 alpha.2 / alpha.5 做 disposable-profile install/uninstall | V3 system/message、replacement `startSeq/endSeq`、PTC event rename 的长期稳定性；是否成为标准观测层 |
| Minimal Harness / byte-stable prompt | 少工具、稳定前缀、压缩输出降低 Harness 干扰 | 实验性 | identity drift 暴露极简 persona 行为边界；官方 0.1.5 又引入动态 system prompt + KV-cache 保持能力 | 可复现 benchmark；极简 prompt 与动态 prompt 是否能同时保持 cache 与身份/约束稳定 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams / Subagent Runtime | 已进入官方 experimental 孵化；continuable Subagent 控制面继续增强，但 Agent ownership / scheduling / Inbox contract 仍在变 | 官方实验性 | `0.1.5-alpha.1` 修正 continuable Subagent ownership，避免被根会话定时调度；移除 `ctx.agent`，调用方需显式传 Agent；`Inbox` 改为 type-only，插件改走 `agent.inbox` | waiting/唤醒、durable relation、foreground/background/continuable 共存、cold recovery、usage 回传；`ctx.agent`/Inbox API 迁移后的插件兼容 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + staged approval，但最新开发线继续改变 Agent/Session API | 可尝鲜 / 需版本匹配 | 0.1.5 移除 `ctx.agent`、调整 Inbox 与 continuable ownership，深度 Agent 插件需重新验证 | **0.1.5-alpha.1** 实际启动/业务验收、复杂任务稳定性、与官方 Agent/Inbox contract 收敛程度 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调 | 实验性 | 官方 Inbox 与 Agent ownership 进一步显式化，降低隐式 root-agent 语义但增加迁移面 | 状态管理、等待/唤醒、故障恢复、成本可观察性、V3 cold resume、Inbox contract |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run/meta-review/自动停止思路 | 自动停止、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH | **稳定候选线仍为 `0.1.2-rc.1`，最新开发基线已直接推进到 `0.1.5-alpha.1`；0.1.5 是新的 Session/Agent/Inbox contract 跳变，不是 alpha.2 的小修** | **RC + 新 Alpha 并行** | 2026-09-08 发布 `0.1.5-alpha.1`：Session format 升 V3，恢复支持的旧会话时生成新日志并保留原文件；system prompt 进入 message history；旧 PTC/code preset 自动迁移；自定义 log reader 必须适配且升级后不可降级读取；同时移除 `ctx.agent`、调整 Inbox API；修复 macOS/Linux `fs-ext` 本地编译要求 | V0/V2→V3 真实迁移、历史 Session 性能/完整性、Windows `fs-ext` 安装是否仍受影响、Plugin Agent/Inbox API、0.1.2 stable 是否推进 |
| 官方 DeepSeek Provider | Provider/附件/模型探测继续进入主干；自定义 Provider models discovery 已增强，但 Web settings namespace 仍有真实回归报告 | Alpha/RC 过渡 | 0.1.3-alpha.2 有 `llm-pi-ai` namespace 未暴露导致自定义 Provider 消失/无法新增的报告；0.1.5 release 未明确宣告修复 | settings 注册是否恢复；Gateway headers、模型能力探测准确性、adapter capability negotiation |
| Codex / ChatGPT Provider | DSH 使用 Codex / ChatGPT 模型通道 | 早期实验 | 0.1.5 可选 Subagent runtime 升级到 Codex 0.153.4 / Claude Code 2.1.263 | 0.1.5 兼容、认证稳定性、模型目录、默认模型语义 |
| 多模型 Router | 按任务复杂度切模型 / Provider | 早期实验 | 0.1.5 新增模型显式声明动态 system prompt / KV-cache 保持能力 | fallback、成本/质量数据、能力探测是否可进入自动路由 |

## 👀 P1｜插件基础设施

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 已实现失败更新精确恢复旧版本/commit + 回读验证 | **0.1.5-alpha.1** compatibility matrix；Session V3、Agent/Inbox API、Update API、供应链、恢复覆盖 |
| Compatibility / Upgrade Skills / upstream-radar | “版本匹配”越来越不足；0.1.5 同时引入 Session V3、Agent API 与 Inbox API 迁移，兼容 gate 必须覆盖 durable log readers 与运行时 Agent seam | 实验性→正在成型 | 0.1.5 发布后，`dsh-context@0.46.1` 已给出 V0/V2/V3 shape-driven seam matrix + disposable-profile install/uninstall 的实证范式 | RC1→0.1.5 real-host gate；V3 migration；custom log reader；Agent/Inbox API；Windows/Linux/macOS install matrix；clean vs in-place upgrade |
| Doctor / Plugin Clinic | 插件故障诊断与恢复 | 可尝鲜 | 已形成启动失败→Session 辅助排障闭环 | 0.1.5 V3 自动修复边界、版本冲突、与 Market 整合 |
| Index / Profile / Distribution | Harness + Plugins 组合成 Agent Profile / Distribution | 早期 | Session V3 + Agent/Inbox API 再次强化“Profile 必须绑定 Harness contract generation” | 版本固定、平台预检、V3 migration、升级/回滚、组合兼容 |
| oh-my-dsh | DSH Distribution 层探索 | 很早期 | 社区 upgrade/compat 方法开始覆盖 V3 generation | 持续维护、0.1.5 migration 覆盖、真实降复杂度能力 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | Claude Code skills/commands/rules/agents/hooks/MCP 复用方向仍有价值，但官方 bridge 曾与 Session contract 脱节；0.1.5 又更新内置 Claude Code runtime | 很早期 / 高兼容风险 | 0.1.5 可选 Subagent runtime 更新 Claude Code 2.1.263；同时 Session V3 / Agent API 变化要求 bridge 重新做 tool-call 与恢复验证 | hooks bridge 是否修复旧 `agent.session.events` 依赖；0.1.5 V3/Agent API；skills/MCP 独立 contract test |
| BrowserSkill | 浏览器登录态 + browser tools / 人工接管 | 可尝鲜 | 已关注 record-safe observation | 权限、安全、0.1.5 Remote/Session lifecycle |
| SSH / Remote / Ops | DSH 向通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | 0.1.3 已支持代理环境；0.1.5 继续调整 Session/Agent 生命周期 | 凭证、安全、审计、代理环境语义、最小权限、第三方 Remote extension seam |
| Memory / Soul | 跨 Workspace Memory / 身份 / 检索注入 | 实验性 | Session V3 把 system prompt 纳入 message history，且 replacement endpoint 形状变化会直接影响 durable reader | V3 迁移、误记、污染、跨项目泄露、成本 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | Web 工作台基础设施；官方 0.1.5 新增实验性右 Sidebar，社区侧栏插件与官方能力开始出现潜在收敛/重叠 | 可日常尝鲜 | 官方 Sidebar 支持多标签、分栏、全屏，并可打开聊天文件链接/产出文件；原 Detail 面板被移除 | 官方 Sidebar 是否覆盖 better-sidebar 的核心价值；第三方页面注册、Session branching、多工作区 |
| dsh-TUI | 正从终端客户端向可承载第三方插件的前端 Runtime 演进 | 可日常尝鲜 | 公开 API/test-utils、toast、permission preset、runtime theme plugin | **0.1.5-alpha.1**、插件接缝稳定性、Session V3、Agent/Inbox API、多 Agent 长期运行 |
| dsh-web-ui | Remote/Git/SSH/Doctor/Task UI 综合增强 | 可尝鲜 | Remote、Recovery、Doctor 持续增强 | 0.1.5、复杂度、安全、官方 Sidebar 重叠 |
| Desktop wrappers | 官方 Harness/Web 的桌面产品层；冻结 Runtime / 原生依赖管理仍有价值 | 可尝鲜 | 0.1.5 修复 macOS/Linux `fs-ext` 本地编译要求，减轻 alpha.2 的一部分原生依赖分发问题 | Windows 原生模块 ABI、V3 Session 迁移、插件隔离、迁移预检、长期 contract 稳定性 |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS、配对、证书 pinning、LAN discovery | 0.1.5、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | Context reclamation / durable working-state；把保存状态与安全回收旧 Context 分开 | 很新；0.1.5 Session V3、system/message、workspace 隔离 |
| dsh-subagent-contract | 重读父/子 Session 日志验证 durable parent/depth/admission/follow-up/report | Research preview；重点验证 0.1.5 Agent ownership/Inbox、V3、cold recovery、one-shot 子 Agent 互操作 |
| dsh-provider-passport | 对自建 / 企业 OpenAI-compatible Provider 做 request-dialect 预检，并映射到 Harness compat 字段后真实 runtime 验证与回滚 | Preview；0.1.5 custom-model/settings、真实网关样本量、误判、最小变更与回滚边界 |
| dsh-plugin-hub / dsh-mcp-manager | Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` | 0.1.5、安全、与 dsh-mcp-lazy 的 Context 成本对比；关注 `tools/list` 分页失控时的 timeout/page-cap |
| dsh-auto-maintenance | 插件自检、快照、失败回滚、rescue | 权限重；0.1.5 Session V3 / 不可降级读取是重要真实检验面 |
| dshvm | DSH 多版本切换与按版本隔离 `$DSH_HOME`，直接对应当前 RC/Alpha 并行与升级污染风险 | 0.1.0 很新；0.1.5 V3 升级后不可降级读取进一步提升隔离价值；重点验证凭据/Session copy、跨平台与回滚可靠性 |

## 官方 DSH 近期里程碑

| 时间 | 版本 / 变化 | 观察意义 |
|---|---|---|
| 2026-08-13 | 0.1.0 RC 系列快速公开 | npm family / plugin 生态加速 |
| 2026-08-19 | 0.1.0-rc.8 | 官方 experimental Agent Teams |
| 2026-08-21 | 0.1.1-rc.1 / rc.2 | Vision / Attachment / Files API 统一化 |
| 2026-08-27 | 0.1.2-alpha.1 | PTC rename、Session/Plugin ABI 明显重构 |
| 2026-08-30 | 0.1.2-alpha.2 | 0.1.2 进入 npm alpha cohort，兼容测试可重复化 |
| 2026-08-31 | 0.1.2-alpha.3 | 长会话/图片投递增强；移除 SQLite Session backend |
| 2026-09-01 | 0.1.2-alpha.4 | Session event seq / log offset contract 拆分；兼容基线再次推进 |
| 2026-09-02 | 0.1.2-alpha.5 | RC 前最后一轮高频 ABI/依赖兼容暴露 |
| 2026-09-03 | 0.1.2-rc.1 | 0.1.2 首个候选版本；Session 按需读取 API、双向 Subagent `send_message`、Remote API 统一 |
| 2026-09-04 | 0.1.3-alpha.1 | SessionHandle + async agentLoop + 跨进程 Session lock + Session format v2；修复空 tool-call ID/name 污染 |
| 2026-09-08 | 0.1.3-alpha.2 | 长会话/恢复性能修复；continuable Subagent 队列/编辑/删除/Steer/停止；Web 断线恢复；引入 `fs-ext` 原生依赖门槛 |
| **2026-09-08** | **0.1.5-alpha.1** | **Session format V3；system prompt 纳入消息历史；旧 PTC/code preset 自动迁移且升级后不可降级读；移除 `ctx.agent`、重构 Inbox API；新增动态 system prompt 不破坏 KV Cache（需模型显式支持）；实验性官方 Sidebar** |

## 当前长期主线

1. **动态能力暴露**：Anchoring、Tool Schema、MCP Lazy、Context/Persona Router，以及官方 dynamic system prompt / KV-cache-preserving capability。
2. **多 Agent 治理**：Agent Teams、Subagent durable relation、Agent ownership / Inbox、foreground/background/continuable 互操作、nested waiting/continuation、执行前审批、usage/成本可观察性。
3. **版本/兼容双线**：稳定候选基线 **0.1.2-rc.1** + 最新开发基线 **0.1.5-alpha.1**；重点验证 Session V3、V0/V2→V3 migration、Agent/Inbox API、clean install + 原地升级、Plugin ABI、Provider/Remote contract。
4. **插件生命周期**：Market、Doctor、rollback、diagnostics、供应链与 Profile/Distribution。
5. **前端 Runtime 平台化**：官方 Sidebar 与 TUI/Web/Desktop 的第三方插件 Runtime / Remote / Session 生命周期逐渐重叠。

## 现在最值得长期盯的对象

1. Anchored Standard / 动态 Tool Schema / dynamic system prompt
2. dsh-routing-suite
3. dsh-mcp-lazy
4. 官方 Agent Teams vs dsh-agent-teams / Agent ownership / Inbox / nested continuation
5. dsh-context V0/V2/V3 compatibility
6. **0.1.5-alpha.1 Session V3 / migration / Agent API / Inbox API / compatibility**
7. dsh-market + Doctor / Compatibility
8. dsh-TUI / better-sidebar / Web UI / Desktop Runtime 与官方 Sidebar 收敛

## 维护规则

- 每天只把**实质增量**写进 `history/YYYY-MM.md`。
- `RADAR.md` 只在当前判断变化时更新。
- 新项目先 Candidate，持续有真实代码 / Release / 兼容验证后再升 P1/P0。
- 普通 Fork、纯换皮、一次性 Demo、Star 波动默认过滤。
- 长期无进展或被官方取代的项目进入 Archive，但历史不删除。
- 当前只观察，不安装 / 下载 / 运行第三方插件。