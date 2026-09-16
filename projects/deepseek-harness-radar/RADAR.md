# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-09-16  
> **迁移到 AI-Tools**：2026-08-29

## 状态定义

- 🔥 **P0**：直接影响 Harness / 推理 / Agent Runtime 的关键方向
- 👀 **P1**：值得持续观察，可能影响工作流或生态成熟度
- 🧪 **Candidate**：新发现，先验证持续性与真实价值
- 💤 **Archive**：长期无实质进展、被官方能力取代或价值下降

## 🔥 P0｜Harness / 推理机制

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| Anchored Standard / 动态 Tool Schema | 仍是最重要的 DSH 推理优化研究线之一；通过控制不同阶段可见 Tool Schema 影响 reasoning trajectory | 实验性 | Prefab seeding / tool unlock 已补；Minimal persona 已确认 identity drift 边界 | 真实任务 trajectory A/B、跨模型复现、identity anchor；sandbox escalation 字段能否按 Session capability 动态投影 |
| dsh-routing-suite | 任务分类 → persona/reasoning 路由 → 近距离 Context 注入；官方已提供“动态修改 system prompt 且不破坏 KV Cache”的模型能力面 | 实验性 | `0.1.5-rc.1` 正式收录 opt-in dynamic system-prompt update without KV-cache invalidation | 支持模型范围；cache hit / trajectory / persona A/B；routing-suite 是否复用官方 capability |
| dsh-mcp-lazy | MCP 工具按需暴露，降低常驻 Schema；0.1.6 Alpha 又暴露 optional MCP provider failure 可拖垮整个 Session activation，fault isolation 仍未闭环 | 可尝鲜 | `0.1.6-alpha.1` Playwright MCP 首连/tools sync 失败可中止无关 Session create/resume | 激活准确率、Schema 成本；provider fault containment；deadline/page-cap；UI error semantics |
| dsh-context | 多 Agent Context / 拓扑可观察层；已主动跨三代 Session log 做 shape-driven 兼容 | 可日常尝鲜 | `dsh-context@0.46.1` 已验证 V0/V2/V3，并对 0.1.5 alpha 做 disposable-profile install/uninstall | `0.1.5-rc.2` / `0.1.6-alpha.1` 实测；system/message、replacement seq、PTC rename 长期稳定性 |
| Minimal Harness / byte-stable prompt | 少工具、稳定前缀、压缩输出降低 Harness 干扰 | 实验性 | 官方 0.1.5 将动态 system prompt + KV-cache 保持推进到 RC | 可复现 benchmark；极简 prompt 与动态 prompt 能否同时保持 cache 与身份/约束稳定 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams / Subagent Runtime | 已进入官方 experimental 孵化；控制面增强明显，但官方 Agent Team profile 与官方 ACP + JSONL persistence 在 0.1.6-alpha.1 最小组合仍可于首个模型请求前失败，跨 surface/persistence 互操作尚未闭环 | 官方实验性 | `0.1.6-alpha.1`：ACP 不挂 Agent Team patch 正常，挂官方 Agent Team profile 后 `session/new` 在 JSONL flush 阶段失败；同类路径此前可在 0.1.5-rc.1 复现 | ACP/Web/headless × JSONL create→prompt→persist→cold resume；waiting/自动唤醒；Steer；usage 回传 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + staged approval；需要重新对齐 0.1.5 Agent/Inbox/Session V3，并与 0.1.6 官方 Agent-Team integration seam 对照 | 可尝鲜 / 需版本匹配 | 官方 0.1.6 Alpha 暴露 Agent Team profile × ACP/JSONL 组合失败，说明“官方实验包”本身也不能作为互操作基准 | rc.2 / alpha.1 实际 boot/复杂任务、one-shot 互操作、与官方 Agent Teams contract 收敛程度 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调；官方 Agent control surface 越来越完整，但等待/恢复与 persistence/surface 互操作仍是关键缺口 | 实验性 | 0.1.6 Alpha 官方 Agent Team profile 在 ACP + JSONL create 阶段出现 integration failure | 状态管理、等待/唤醒、故障恢复、成本可观察性、V3 cold resume、跨 surface persistence |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run/meta-review/自动停止思路 | 自动停止、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH | **稳定候选主基线仍为 `0.1.5-rc.2`；新增 `0.1.6-alpha.1` 前瞻开发线。0.1.6 已出现官方包族 bundle manifest、peer/scope identity、Agent Team × ACP/JSONL 等 integration correctness 风险，不应与 RC 基线混用。** | **RC 主线 + Alpha 前瞻** | 2026-09-15～16：0.1.6-alpha.1 官方 computer-use 包缺新 loader 所需 `dsh.bundle`；browser-use runtime 重复 `dsh-scope` 物理 copy 可破坏 scoped context；Agent Team profile × ACP/JSONL create 失败 | 0.1.6 package/bundle/peer topology 收口；0.1.5 stable；Session writer/migration；跨 surface/persistence matrix |
| Session V3 / migration & compaction | V3 已进入 RC，但风险涵盖历史 migration、现役 writer correctness 与长期会话 compaction：结构合法并不保证 reasoning model 下 summary budget 足够 | RC / 高迁移与完整性风险 | 2026-09-16 新报告指出 `/compact` 默认 8192 token budget 在 reasoning model 上可被 reasoning tokens 吃掉而持续无法生成 summary；相关默认在 0.1.6-alpha.1 仍存在 | writer fix；V2→V3 repair；compaction reasoning/output budget；provider usage accounting；strict cold reopen |
| 官方 DeepSeek Provider | Provider/模型探测继续成熟；此前 `llm-pi-ai` 无效配置导致整个模型设置入口消失的问题已在 0.1.5 RC release notes 明确修复 | RC | `0.1.5-rc.1` 新增 DeepSeek-V41-Flash 默认模型、任意历史 system prompt update；修复失效 pi-ai 配置吞掉模型设置入口，并加强 Base URL 校验 | reasoning token accounting、Gateway dialect、模型 capability negotiation、默认模型切换影响 |
| Codex / ChatGPT Provider | 社区 Codex provider 已出现 `0.1.5-rc.2` exact-pairing，并有项目声称继续覆盖 `0.1.6-alpha.1`；仍需真实账户/请求与 Session 恢复证据 | Community Alpha / 可尝鲜但需版本匹配 | `relay-dsh-plugin-codex 0.2.3` 声称同时验证 0.1.5-rc.2 与 0.1.6-alpha.1 durable/live Assistant stream、persistence response shape 与 settlement metadata | real-account acceptance、Session recovery/compaction、认证稳定性、0.1.6 integration drift |
| 多模型 Router | 按任务复杂度切模型 / Provider；reasoning token accounting 已成为长期会话路由的新约束 | 早期实验 | 0.1.6 Alpha compaction 报告显示 reasoning model 不能只按总 maxTokens 估算 summarizer 可用输出 | fallback、成本/质量数据、reasoning/output budget、能力探测自动路由 |

## 👀 P1｜插件基础设施 / Security

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 已实现失败更新精确恢复旧版本/commit + 回读验证 | 0.1.6 bundle manifest / peer topology；Session V3、Agent/Inbox、Panel/RPC API、供应链、恢复覆盖 |
| Compatibility / Upgrade Skills / upstream-radar | “版本匹配”远远不足；兼容 gate 已扩大为 install/platform → bundle/peer topology → Profile/Preset migration → Host/Client RPC → assistant stream/tool/MCP → Session migration/cold recovery/writer integrity | 实验性→正在成型 | 0.1.6-alpha.1 官方包族自身出现缺 `dsh.bundle` 与 duplicate `dsh-scope` identity 问题，证明 package topology 必须成为一级 gate | exact version card；bundle manifest；physical dependency identity；writer integrity；Host RPC；V3 corpus；clean vs in-place upgrade |
| Plugin Web/RPC extension seam | 0.1.5 RC 出现公开 `connection.rpc.handle()` 系统性失败：第三方 Web/RPC channel 无法注册，POST 落到 SPA fallback 405；agent-side tools可仍正常，容易形成“半兼容”假象 | RC Plugin ABI 回归 | 公开报告已涉及 dsh-mnemon、dsh-vision-router；rc.2 release notes 未声明修复 | rc.2 / alpha.1 exact-tag real-host；authenticated RPC round-trip；Panel/Sidebar 扩展面是否收敛 |
| Doctor / Plugin Clinic | 插件故障诊断与恢复；0.1.6 package topology 让“能 import”不再等于“能作为 profile bundle boot” | 可尝鲜 | 0.1.6-alpha.1 computer-use bundle 缺 manifest 的社区复核指出部分 boot-check 可假绿灯 | bundle manifest、peer duplication、V3/旧 preset/RPC 自动诊断、与 Market 整合 |
| Index / Profile / Distribution | Harness + Plugins 组合成 Agent Profile / Distribution；必须同时管理持久 schema 与 package/bundle/peer topology | 早期 | 0.1.6-alpha.1 新 loader 严格 bundle contract 与已发布官方包 metadata 不一致，可按文档安装后直接 boot fail | bundle schema 预检、peer identity、preset migration、V3 migration、升级/回滚 |
| Web fetch / Proxy SSRF boundary | 0.1.5 支持全局 HTTP(S) proxy，但代理分支 hostname public-address resolution/pinning 风险仍待官方处置 | RC 风险 / 待官方处置 | 2026-09-09 社区报告；rc.1 tag 复核可见 proxied branch 直接 `requestVia` | rc.2/0.1.6 是否变化；proxy-side DNS policy/allowlist；NO_PROXY/企业代理语义 |
| Storage JSON legacy bootstrap | 0.1.5-alpha.1 有 legacy bootstrap record key 未校验导致 path traversal / arbitrary write 的公开报告；暂未见明确修复结论 | 待确认安全风险 | 2026-09-09 新报告 | 0.1.6 代码核验、官方安全响应、legacy migration 默认可达性 |
| oh-my-dsh | DSH Distribution 层探索 | 很早期 | 社区 upgrade/compat 方法已覆盖 RC/Alpha 多走廊 | 持续维护、0.1.6 package topology、真实降复杂度能力 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | Claude Code skills/commands/rules/agents/hooks/MCP 复用方向仍有价值，但官方 bridge 曾与 Session contract 脱节 | 很早期 / 高兼容风险 | 0.1.5/0.1.6 的 Session/Agent/package contract 继续快速变化 | hooks bridge、V3/Agent API、bundle/peer topology、skills/MCP 独立 contract test |
| BrowserSkill | 浏览器登录态 + browser tools / 人工接管；0.1.6 官方 browser-use 已暴露 package identity 与 MCP fault-isolation 问题 | 可尝鲜 / Alpha integration 风险 | 0.1.6-alpha.1 Playwright MCP 首连失败可中止整个 Session；browser-use runtime duplicate `dsh-scope` 可破坏多 Session | 权限、安全、MCP fault containment、scope identity、Session lifecycle |
| SSH / Remote / Ops | DSH 向通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | 0.1.5 RC 将 proxy、Session lock、Agent cold delivery 合并进候选版 | 凭证、安全、审计、代理语义、最小权限、第三方 Remote extension seam |
| Memory / Soul | 跨 Workspace Memory / 身份 / 检索注入仍有价值，但 V3 严格迁移已证明第三方 durable event 会反向影响历史可加载性 | 实验性 / 需严格 durable-event contract | `dsh-evolve v0.5.2` 修复 notice 注入缺 `source.summary`；旧 Harness 宽松、0.1.5 V3 migration 严格 | V3 event schema；注入 metadata；误记/污染；迁移前审计与修复 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | 官方 0.1.5 Sidebar 已进入 RC，社区侧栏插件与官方能力重叠显著上升 | 可日常尝鲜 / 差异化承压 | RC1 Sidebar 支持多标签、分栏、全屏与多格式文件预览/交付 | 第三方页面、Session branching、多 Workspace、终端 park；Host RPC seam |
| dsh-TUI | 正从终端客户端向可承载第三方插件的前端 Runtime 演进 | 可日常尝鲜 | 公开 API/test-utils、toast、permission preset、runtime theme plugin | 0.1.5-rc.2 / 0.1.6-alpha.1、Session V3、Agent/Inbox、长期多 Agent |
| dsh-web-ui | Remote/Git/SSH/Doctor/Task UI 综合增强 | 可尝鲜 | 官方 Sidebar/文件交付进入 RC，重叠进一步增加 | 0.1.6、复杂度、安全、官方能力重叠后的不可替代功能 |
| Desktop wrappers | 官方 Harness/Web 的桌面产品层；0.1.6 Alpha 已出现 ASAR/PTC 与 native computer-use integration 风险 | 可尝鲜 / Alpha 风险高 | 0.1.6-alpha.1 packaged Desktop 有 PTC worker-exit 与 Windows CUA snapshot/DPI integration 报告 | ASAR runtime、Windows native ABI、CUA metadata projection、V3 migration、插件隔离 |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS、配对、证书 pinning、LAN discovery | 0.1.6、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | Context reclamation / durable working-state；把保存状态与安全回收旧 Context 分开 | 很新；RC Session V3、system/message、workspace 隔离 |
| dsh-subagent-contract | 重读父/子 Session 日志验证 durable parent/depth/admission/follow-up/report | Research preview；重点验证 RC ownership/Inbox、V3、cold recovery、one-shot 互操作 |
| dsh-provider-passport | 对自建 / 企业 OpenAI-compatible Provider 做 request-dialect 预检，并映射 Harness compat 字段后真实 runtime 验证与回滚 | Preview；RC custom-model/settings、真实网关样本量、误判、最小变更与回滚边界 |
| dsh-plugin-hub / dsh-mcp-manager | Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` | 继续比较 timeout、provider fault containment、安全、Schema 成本与 dsh-mcp-lazy |
| dsh-auto-maintenance | 插件自检、快照、失败回滚、rescue | 权限重；RC Session V3 / 不可降级读取与 0.1.6 package topology 是重要检验面 |
| dshvm | DSH 多版本切换与按版本隔离 `$DSH_HOME`，直接对应 RC/Alpha 并行与升级污染风险 | 很新；重点验证凭据/Session copy、跨平台、0.1.6 Alpha 隔离与回滚可靠性 |
| dsh-plugin-upgrade | 锁定 0.1.3-alpha.1→0.1.5 迁移走廊，提供只读 seam scanner + on-demand upgrade skill；报告使用 40 个真实插件仓做 seam 语料 | 需继续覆盖 `0.1.5-rc.2`→`0.1.6-alpha.1` bundle/peer topology 与 real-host gate |
| dsh-sandbox-escalation-fix | 针对 Full Access / delegated Subagent 重复 escalation；多份独立复现并给出 rc.2 compatibility | 重点看官方 session-aware Tool Schema projection / same-mode normalization、跨模型 A/B、real-host retry/token 数据 |

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
| **2026-09-10** | **0.1.5-rc.2** | **当前稳定候选主基线；Runtime/Session correctness 仍在验证** |
| **2026-09-15** | **0.1.6-alpha.1** | **新增前瞻开发线；官方 package/bundle/peer topology、Agent Team × ACP/JSONL、Browser/MCP/Desktop integration seam 已出现真实回归，不作为日常基线** |

## 当前长期主线

1. **动态能力暴露**：Anchoring、Tool Schema、MCP Lazy、Context/Persona Router、dynamic system prompt / KV-cache-preserving capability；sandbox escalation 字段是否按 Session capability 动态投影。
2. **多 Agent 治理**：Agent Teams、Subagent durable relation、Agent ownership / Inbox、跨 surface/persistence create→prompt→persist→cold resume、nested waiting/continuation、Steer、usage/成本。
3. **双版本兼容基线**：日常/候选主线 **0.1.5-rc.2**；前瞻开发线 **0.1.6-alpha.1**。重点验证 bundle/peer topology、Profile/Preset、Host/Client RPC、assistant stream/tool、Session V3、Agent/Inbox/Panel API。
4. **Runtime / Security**：Session migration/lock/compaction/writer correctness、reasoning-token budget、MCP fault isolation、sandbox schema projection、proxy/web-fetch SSRF、storage migration path safety。
5. **插件生命周期**：Market、Doctor、upgrade skill、rollback、diagnostics、供应链与 Profile/Distribution；新增 package physical identity / bundle manifest 检查。
6. **前端 Runtime 平台化**：官方 Sidebar 与 TUI/Web/Desktop/Browser/Computer-use 的第三方 Runtime、native packaging 与 Session 生命周期逐渐重叠。

## 现在最值得长期盯的对象

1. Anchored Standard / 动态 Tool Schema / dynamic system prompt
2. dsh-routing-suite
3. dsh-mcp-lazy + MCP Runtime fault isolation
4. 官方 Agent Teams vs dsh-agent-teams / Agent ownership / Inbox / cross-surface persistence
5. dsh-context V0/V2/V3 compatibility
6. **0.1.5-rc.2 Session V3 migration/writer/compaction + 0.1.6-alpha.1 integration correctness**
7. dsh-market + Doctor / Compatibility / dsh-plugin-upgrade
8. Web fetch / Proxy / Storage security boundary
9. Codex / ChatGPT Provider exact-pairing 与真实请求恢复
10. dsh-sandbox-escalation-fix / session-aware sandbox Tool Schema
11. dsh-TUI / better-sidebar / Web UI / Desktop / Browser / Computer-use Runtime 收敛

## 维护规则

- 每天只把**实质增量**写进 `history/YYYY-MM.md`。
- `RADAR.md` 只在当前判断变化时更新。
- 新项目先 Candidate，持续有真实代码 / Release / 兼容验证后再升 P1/P0。
- 普通 Fork、纯换皮、一次性 Demo、Star 波动默认过滤。
- 长期无进展或被官方取代的项目进入 Archive，但历史不删除。
- 当前只观察，不安装 / 下载 / 运行第三方插件。