# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-09-12  
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
| dsh-routing-suite | 任务分类 → persona/reasoning 路由 → 近距离 Context 注入；官方已提供“动态修改 system prompt 且不破坏 KV Cache”的模型能力面 | 实验性 | `0.1.5-rc.1` 正式收录 opt-in dynamic system-prompt update without KV-cache invalidation | 支持模型范围；cache hit / trajectory / persona A/B；routing-suite 是否复用官方 capability |
| dsh-mcp-lazy | MCP 工具按需暴露，降低常驻 Schema | 可尝鲜 | `0.1.5-rc.1` 官方拒绝 MCP 重复分页 cursor，避免启动/同步无限等待并保留上一组可用工具 | RC 系列真实兼容、激活准确率、Schema 成本；是否还需要额外 deadline/page-cap |
| dsh-context | 多 Agent Context / 拓扑可观察层；已主动跨三代 Session log 做 shape-driven 兼容 | 可日常尝鲜 | `dsh-context@0.46.1` 已验证 V0/V2/V3，并对 0.1.5 alpha 做 disposable-profile install/uninstall | `0.1.5-rc.2` V3 实测；system/message、replacement seq、PTC rename 长期稳定性 |
| Minimal Harness / byte-stable prompt | 少工具、稳定前缀、压缩输出降低 Harness 干扰 | 实验性 | 官方 0.1.5 将动态 system prompt + KV-cache 保持推进到 RC | 可复现 benchmark；极简 prompt 与动态 prompt 能否同时保持 cache 与身份/约束稳定 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams / Subagent Runtime | 已进入官方 experimental 孵化；0.1.5 RC 发布可安装 Agent Teams 包，continuable Subagent 控制面明显增强，但 durable continuation 仍未完全闭环 | 官方实验性 | `0.1.5-rc.1` 汇总队列/编辑/删除/Steer/停止、跨 Agent 冷恢复 sender attribution/order、continuable ownership 修正；实验性 Agent Teams 包可从 npm 显式安装 | waiting/自动唤醒、foreground/background/continuable 共存、cold recovery、usage 回传、阻塞 `job_output(wait)` 下 steer 抢占 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + staged approval；需要重新对齐 0.1.5 Agent/Inbox/Session V3 | 可尝鲜 / 需版本匹配 | 官方 0.1.5 RC 固化移除 `ctx.agent`、`agent.inbox` 与 continuable ownership 新语义 | rc.2 实际 boot/复杂任务、one-shot 互操作、与官方 Agent Teams contract 收敛程度 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调；官方 Agent control surface 越来越完整，但等待/恢复语义仍是关键缺口 | 实验性 | 0.1.5 RC 将 Subagent 队列、Steer、停止、cold delivery 纳入候选版 | 状态管理、等待/唤醒、故障恢复、成本可观察性、V3 cold resume、阻塞工具下 steer 延迟 |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run/meta-review/自动停止思路 | 自动停止、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH | **最新稳定候选基线仍为 `0.1.5-rc.2`；rc.2 本身仅做 UI 优化，但现役 Session writer / V3 migration 仍有真实 correctness 风险。`0.1.2-rc.1` 保留为旧 RC 对照线。** | **RC** | 2026-09-12 新证据确认 `0.1.5-rc.2` 在“failed assistant attempt + next-turn steering splice”路径仍可写出缺失 `turn/end` 的 durable Session 形态，后续严格读取可失败 | writer-side turn closure；V2→V3 repair；旧 preset schema；Host↔Client RPC；assistant streaming；0.1.5 stable |
| Session V3 / migration | V3 已进入 RC，但风险已从“历史 corpus 迁移不全”扩大到**当前 writer correctness**：旧 descriptor / unclassified source 会 fail-closed，rc.2 特定 steering 路径还可新写出缺 `turn/end` 的 durable hole | RC / 高迁移与完整性风险 | `0.1.5-rc.2` 实证：failed `assistant/attempt` 后 `agent/inbox/spliced target=next-turn` 可直接进入下一 `turn/start` 而不写前一 `turn/end`；同类 stored-v2 artifact 在 V3 migration 会关系校验失败 | 官方 writer fix；v2→v3 是否做 repair-not-skip；多来源 corpus；迁移后 compaction/cold reopen；不可降级边界 |
| 官方 DeepSeek Provider | Provider/模型探测继续成熟；此前 `llm-pi-ai` 无效配置导致整个模型设置入口消失的问题已在 0.1.5 RC release notes 明确修复 | RC | `0.1.5-rc.1` 新增 DeepSeek-V41-Flash 默认模型、任意历史 system prompt update；修复失效 pi-ai 配置吞掉模型设置入口，并加强 Base URL 校验 | 自定义 Provider settings 的真实 RC 回归；Gateway dialect、模型 capability negotiation、默认模型切换影响 |
| Codex / ChatGPT Provider | 社区 Codex provider 已出现 `0.1.5-rc.2` exact-pairing 与 doctor / isolated-install 验证，方向从概念实验进入可验证 Community Alpha；仍依赖 ChatGPT OAuth 与上游模型权限 | Community Alpha / 可尝鲜但需版本匹配 | `dsh-codex-connect 0.1.0-alpha.4.35` 明确列出 `0.1.2-rc.1 / 0.1.5-alpha.1 / rc.1 / rc.2` verified pairing，并强调 doctor 不能替代真实请求验收 | real-account acceptance、Session recovery/compaction、认证稳定性、模型目录、RC 后续版本漂移 |
| 多模型 Router | 按任务复杂度切模型 / Provider | 早期实验 | 0.1.5 RC 支持模型显式声明 dynamic system prompt / KV-cache 能力 | fallback、成本/质量数据、能力探测能否进入自动路由 |

## 👀 P1｜插件基础设施 / Security

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 已实现失败更新精确恢复旧版本/commit + 回读验证 | `0.1.5-rc.2` compatibility matrix；Session V3、Agent/Inbox、Panel/RPC API、供应链、恢复覆盖 |
| Compatibility / Upgrade Skills / upstream-radar | “版本匹配”不足；0.1.5 RC 后兼容 gate 已扩大为 install/platform → Profile/Preset migration → Host/Client RPC → assistant stream/tool/MCP → Session migration/cold recovery/writer integrity | 实验性→正在成型 | rc.2 又新增现役 writer 可制造 durable `turn/end` hole 的真实证据，说明只测旧日志迁移仍不够 | rc.2 exact version card；writer integrity；preset schema migration；Host RPC POST；assistant text/thinking/tool assertion；V3 corpus migration；clean vs in-place upgrade |
| Plugin Web/RPC extension seam | 0.1.5 RC 出现公开 `connection.rpc.handle()` 系统性失败：第三方 Web/RPC channel 无法注册，POST 落到 SPA fallback 405；agent-side tools 可仍正常，容易形成“半兼容”假象 | RC Plugin ABI 回归 | 公开报告已涉及 dsh-mnemon、dsh-vision-router；rc.2 release notes 未声明修复 | rc.2 exact-tag real-host；官方 service injection 语义；authenticated RPC round-trip；Panel/Sidebar 扩展面是否收敛 |
| Doctor / Plugin Clinic | 插件故障诊断与恢复 | 可尝鲜 | 已形成启动失败→Session 辅助排障闭环 | RC V3/旧 preset/RPC 自动诊断边界、版本冲突、与 Market 整合 |
| Index / Profile / Distribution | Harness + Plugins 组合成 Agent Profile / Distribution | 早期；0.1.5 RC 已证明 Profile 不仅要固定包版本，还必须迁移持久 preset/schema | 0.1.5 persona `text→prefix` 未迁移旧自定义 preset，可让所有新 Session 创建失败且重装后仍保留故障状态 | 版本固定、preset schema 预检/迁移、平台预检、V3 migration、升级/回滚、组合兼容 |
| Web fetch / Proxy SSRF boundary | **新增安全观察项**：0.1.5 支持全局 HTTP(S) proxy，但 RC1 的代理分支仍跳过 hostname 的 public-address resolution/pinning，只拦非公网 IP literal；域名若由代理解析到内网地址存在 SSRF 风险面 | RC 风险 / 待官方处置 | 2026-09-09 社区报告；对 `dsh-v0.1.5-rc.1` tag 的 `web-fetch-http/provider.ts` 复核仍可见 proxied branch 直接 `requestVia` 的逻辑 | rc.2 tag 是否变化；官方是否引入 proxy-side DNS policy/allowlist；NO_PROXY/企业代理语义；间接 prompt injection → internal fetch 威胁模型 |
| Storage JSON legacy bootstrap | 0.1.5-alpha.1 有 legacy single→per-record bootstrap record key 未校验导致 path traversal / arbitrary write 的公开报告；暂未看到 RC release notes 明确修复 | 待确认安全风险 | 2026-09-09 新报告 | rc.2 tag 代码核验、官方安全响应、legacy migration 是否默认可达、数据来源边界 |
| oh-my-dsh | DSH Distribution 层探索 | 很早期 | 社区 upgrade/compat 方法已覆盖 RC/Alpha 多走廊 | 持续维护、0.1.5 RC migration、真实降复杂度能力 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | Claude Code skills/commands/rules/agents/hooks/MCP 复用方向仍有价值，但官方 bridge 曾与 Session contract 脱节 | 很早期 / 高兼容风险 | 0.1.5 RC 内置 Claude Code runtime 更新，同时 Session V3 / Agent API 固化 | hooks bridge 是否修复旧 `agent.session.events`；RC V3/Agent API；skills/MCP 独立 contract test |
| BrowserSkill | 浏览器登录态 + browser tools / 人工接管 | 可尝鲜 | 0.1.5 RC 全局 proxy 与 web-fetch 安全边界成为新风险面 | 权限、安全、SSRF/内网访问、record-safe observation、Session lifecycle |
| SSH / Remote / Ops | DSH 向通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | 0.1.5 RC 将 proxy、Session lock、Agent cold delivery 合并进候选版 | 凭证、安全、审计、代理语义、最小权限、第三方 Remote extension seam |
| Memory / Soul | 跨 Workspace Memory / 身份 / 检索注入仍有价值，但 V3 严格迁移已证明第三方写入事件的 source metadata 会反过来影响整个历史会话可加载性 | 实验性 / 需严格 durable-event contract | `dsh-evolve v0.5.2` 修复其 notice 注入缺 `source.summary`：旧 Harness 未严格校验，但 `0.1.5-rc.2` v0→v1 migration 会拒绝含该形态的整段历史 | V3 event schema；注入 metadata contract；误记/污染；跨项目泄露；迁移前审计与修复 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | 官方 0.1.5 Sidebar 已从实验 alpha 进入 RC，社区侧栏插件与官方能力重叠显著上升 | 可日常尝鲜 / 差异化承压 | RC1 Sidebar 支持多标签、分栏、全屏、Markdown/代码/HTML/PDF/图片预览、模型显式交付文件；插件 Panel API 改为 `sidebar.panellist` / `main` | 第三方页面、Session branching、多 Workspace、终端 park 等差异化是否仍足够；Host RPC seam 是否影响扩展页面 |
| dsh-TUI | 正从终端客户端向可承载第三方插件的前端 Runtime 演进 | 可日常尝鲜 | 公开 API/test-utils、toast、permission preset、runtime theme plugin | `0.1.5-rc.2`、Session V3、Agent/Inbox、长期多 Agent 运行 |
| dsh-web-ui | Remote/Git/SSH/Doctor/Task UI 综合增强 | 可尝鲜 | 官方 Sidebar/文件交付进入 RC，重叠进一步增加 | RC2、复杂度、安全、官方能力重叠后的不可替代功能 |
| Desktop wrappers | 官方 Harness/Web 的桌面产品层；冻结 Runtime / 原生依赖管理仍有价值 | 可尝鲜 | 0.1.5 修复部分 `fs-ext` 分发问题，但原地升级 client bundle 仍需真实验证 | Windows native ABI、V3 migration、client combo、插件隔离、迁移预检 |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS、配对、证书 pinning、LAN discovery | RC2、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | Context reclamation / durable working-state；把保存状态与安全回收旧 Context 分开 | 很新；RC Session V3、system/message、workspace 隔离 |
| dsh-subagent-contract | 重读父/子 Session 日志验证 durable parent/depth/admission/follow-up/report | Research preview；重点验证 RC ownership/Inbox、V3、cold recovery、one-shot 互操作 |
| dsh-provider-passport | 对自建 / 企业 OpenAI-compatible Provider 做 request-dialect 预检，并映射 Harness compat 字段后真实 runtime 验证与回滚 | Preview；RC custom-model/settings、真实网关样本量、误判、最小变更与回滚边界 |
| dsh-plugin-hub / dsh-mcp-manager | Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` | RC 已修重复 cursor；继续比较 timeout、安全、Schema 成本与 dsh-mcp-lazy |
| dsh-auto-maintenance | 插件自检、快照、失败回滚、rescue | 权限重；RC Session V3 / 不可降级读取是重要真实检验面 |
| dshvm | DSH 多版本切换与按版本隔离 `$DSH_HOME`，直接对应 RC 并行与升级污染风险 | 很新；RC/V3 下重点验证凭据/Session copy、跨平台与回滚可靠性 |
| dsh-plugin-upgrade | 锁定 0.1.3-alpha.1→0.1.5 迁移走廊，提供只读 seam scanner + on-demand upgrade skill；报告使用 40 个真实插件仓做 seam 语料 | 新项目；需把终点更新到 `0.1.5-rc.2` 并证明 preset/RPC/stream/V3 real-host gate 持续有效 |

## 官方 DSH 近期里程碑

| 时间 | 版本 / 变化 | 观察意义 |
|---|---|---|
| 2026-08-13 | 0.1.0 RC 系列快速公开 | npm family / plugin 生态加速 |
| 2026-08-19 | 0.1.0-rc.8 | 官方 experimental Agent Teams |
| 2026-08-21 | 0.1.1-rc.1 / rc.2 | Vision / Attachment / Files API 统一化 |
| 2026-08-27 | 0.1.2-alpha.1 | PTC rename、Session/Plugin ABI 明显重构 |
| 2026-08-30 | 0.1.2-alpha.2 | 0.1.2 进入 npm alpha cohort，兼容测试可重复化 |
| 2026-08-31 | 0.1.2-alpha.3 | 长会话/图片投递增强；移除 SQLite Session backend |
| 2026-09-01 | 0.1.2-alpha.4 | Session event seq / log offset contract 拆分 |
| 2026-09-02 | 0.1.2-alpha.5 | RC 前最后一轮 ABI/依赖兼容暴露 |
| 2026-09-03 | 0.1.2-rc.1 | 0.1.2 首个候选版本；Session 按需读取 API、双向 Subagent `send_message`、Remote API 统一 |
| 2026-09-04 | 0.1.3-alpha.1 | SessionHandle + async agentLoop + Session lock + Session v2；修复空 tool-call ID/name 污染 |
| 2026-09-08 | 0.1.3-alpha.2 | 长会话/恢复性能；continuable Subagent 控制面；Web 断线恢复 |
| 2026-09-08 | 0.1.5-alpha.1 | Session V3、dynamic system prompt/KV cache、Agent/Inbox API、官方 Sidebar |
| 2026-09-09 | 0.1.5-alpha.2 | Sidebar 文档预览/Deliverables、Panel API、minimal 默认工具调整、Agent Teams npm 包 |
| 2026-09-10 | 0.1.5-rc.1 | 0.1.5 首个 RC：V3/Agent/Sidebar/Provider 能力进入候选线；修复空 tool-call identity、失效 pi-ai 设置入口、MCP 重复 cursor；新增 DeepSeek-V41-Flash 默认模型与任意文件上传 |
| **2026-09-10** | **0.1.5-rc.2** | **当前最新 RC；仅反馈提交流程、交付文件卡片/间距/代码图标等 UI 体验优化，未体现新的 Runtime/Plugin contract 收口** |

## 当前长期主线

1. **动态能力暴露**：Anchoring、Tool Schema、MCP Lazy、Context/Persona Router、dynamic system prompt / KV-cache-preserving capability。
2. **多 Agent 治理**：Agent Teams、Subagent durable relation、Agent ownership / Inbox、foreground/background/continuable 互操作、nested waiting/continuation、Steer 抢占、usage/成本可观察性。
3. **RC 兼容基线**：当前主基线 **0.1.5-rc.2**；重点验证 Profile/Preset 持久 schema、Host/Client RPC、assistant stream/tool、Session V3 历史迁移与 writer integrity、Agent/Inbox/Panel API、clean install + 原地升级。
4. **Runtime / Security**：Session migration/lock/compaction/writer correctness、MCP fault isolation、proxy/web-fetch SSRF、storage migration path safety。
5. **插件生命周期**：Market、Doctor、upgrade skill、rollback、diagnostics、供应链与 Profile/Distribution。
6. **前端 Runtime 平台化**：官方 Sidebar 与 TUI/Web/Desktop 的第三方 Runtime / Remote / Session 生命周期逐渐重叠。

## 现在最值得长期盯的对象

1. Anchored Standard / 动态 Tool Schema / dynamic system prompt
2. dsh-routing-suite
3. dsh-mcp-lazy + MCP Runtime fault isolation
4. 官方 Agent Teams vs dsh-agent-teams / Agent ownership / Inbox / nested continuation / steer
5. dsh-context V0/V2/V3 compatibility
6. **0.1.5-rc.2 Profile/Preset migration / Host RPC / assistant stream / Session V3 migration + writer integrity**
7. dsh-market + Doctor / Compatibility / dsh-plugin-upgrade
8. Web fetch / Proxy / Storage security boundary
9. Codex / ChatGPT Provider exact-pairing 与真实请求恢复
10. dsh-TUI / better-sidebar / Web UI / Desktop Runtime 与官方 Sidebar 收敛

## 维护规则

- 每天只把**实质增量**写进 `history/YYYY-MM.md`。
- `RADAR.md` 只在当前判断变化时更新。
- 新项目先 Candidate，持续有真实代码 / Release / 兼容验证后再升 P1/P0。
- 普通 Fork、纯换皮、一次性 Demo、Star 波动默认过滤。
- 长期无进展或被官方取代的项目进入 Archive，但历史不删除。
- 当前只观察，不安装 / 下载 / 运行第三方插件。