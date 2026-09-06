# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-09-06  
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
| dsh-routing-suite | 任务分类 → persona/reasoning 路由 → 近距离 Context 注入 | 实验性 | router 与 runtime injection 已合并并通过项目自测 | 正式发布、真实 ablation、benchmark 泛化 |
| dsh-mcp-lazy | MCP 工具按需暴露，降低常驻 Schema | 可尝鲜 | 多版 DSH 已有验证 | **0.1.3-alpha.1** 兼容、激活准确率、与 MCP Manager 对比 |
| dsh-context | 多 Agent Context / 拓扑可观察层 | 可日常尝鲜 | 0.38.x 已处理早期 0.1.2 projection contract 变化 | **0.1.3-alpha.1** SessionHandle/Session v2 验证；是否成为标准观测层 |
| Minimal Harness / byte-stable prompt | 少工具、稳定前缀、压缩输出降低 Harness 干扰 | 实验性 | identity drift 暴露极简 persona 的行为边界 | 可复现 benchmark；极简与身份/约束锚定平衡 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams / Subagent Runtime | 已进入官方 experimental 孵化；0.1.3-alpha.1 继续强化跨 Agent / 冷恢复消息语义，但与其他 Subagent 模式互操作仍需验证 | 官方实验性 | `send_message` 在 0.1.3-alpha.1 统一为 steer 语义，并在跨 Agent 与 cold recovery 投递中保留发送者归属和顺序 | Session v2 / SessionHandle 下 waiting/唤醒、durable relation、消息有序性；foreground/background/continuable 共存；usage 回传 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + staged approval，但 0.1.2/0.1.3 线持续存在 Runtime ABI 风险 | 可尝鲜 / 需版本匹配 | RC1 已出现 foreground one-shot 互操作问题；0.1.3-alpha.1 又改变 Session lifecycle/persistence contract | **0.1.3-alpha.1** 实际启动/业务验收、复杂任务稳定性、与官方 `send_message`/SessionHandle 收敛程度 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调 | 实验性 | 官方 `send_message` 冷恢复语义增强，但 SessionHandle 与 Session v2 使持久化/恢复 contract 再次变化 | 状态管理、等待/唤醒、故障恢复、成本可观察性、Session v2 cold resume |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run/meta-review/自动停止思路 | 自动停止、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH | **稳定候选线仍为 `0.1.2-rc.1`，但最新开发基线已推进到 `0.1.3-alpha.1`；Session lifecycle/persistence 再次发生破坏性变化** | **RC + 新 Alpha 并行** | 0.1.3-alpha.1 引入 lifecycle-scoped `SessionHandle`、异步 `agentLoop.create()`、跨进程 Session lock 与 Session format v2；同时修复空 tool-call ID/name 导致会话不可重开的故障 | 0.1.3 alpha 后续性能修复；Session v0/v1→v2 迁移、跨进程锁、历史 Session 加载、Plugin ABI；0.1.2 stable 是否继续推进 |
| 官方 DeepSeek Provider | Provider/附件/模型探测继续进入主干；0.1.3-alpha.1 增强自定义 Provider models discovery | Alpha/RC 过渡 | 支持自定义 Provider `models` 对象和 Anthropic 原生模型列表，并回填模型名、context window、max output token；修复 DeepSeek 流式工具调用续传覆盖 ID/name | 自定义 Provider settings 注册是否稳定；Gateway headers、模型能力探测准确性、adapter capability negotiation |
| Codex / ChatGPT Provider | DSH 使用 Codex / ChatGPT 模型通道 | 早期实验 | RC1 子代理模型选择支持 Codex；社区 provider 已有 RC1 验证记录 | 0.1.3-alpha.1 兼容、认证稳定性、模型目录、pi-ai 边界 |
| 多模型 Router | 按任务复杂度切模型 / Provider | 早期实验 | tier-router / routing-suite 等方向 | fallback、成本/质量数据、真实自动路由价值；0.1.3 model discovery 影响 |

## 👀 P1｜插件基础设施

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 已实现失败更新精确恢复旧版本/commit + 回读验证 | **0.1.3-alpha.1** compatibility matrix；SessionHandle/Session v2、Update API、供应链、恢复覆盖 |
| Compatibility / Upgrade Skills / upstream-radar | 0.1.3-alpha.1 再次证明兼容不能只看 peer range：Session persistence/lifecycle 已跨代 | 实验性→正在成型 | RC1 已暴露原地升级/混合依赖问题；0.1.3-alpha.1 新增 `SessionHandle`、异步 agentLoop、Session v2 与跨进程锁，形成新的 exact-contract 迁移面 | **RC1→0.1.3-alpha.1** real-host gate；v0/v1→v2 Session migration、clean vs in-place upgrade、依赖树污染、exact API surface、官方 Upgrade Skill |
| Doctor / Plugin Clinic | 插件故障诊断与恢复 | 可尝鲜 | 已形成启动失败→Session 辅助排障闭环 | 0.1.3-alpha.1、Session v2 自动修复边界、版本冲突、与 Market 整合 |
| Index / Profile / Distribution | Harness + Plugins 组合成 Agent Profile / Distribution | 早期 | 0.1.2/0.1.3 的 profile/core bundle 与 Session ABI 漂移强化 Profile contract 版本化需求 | 版本固定、预检、升级/回滚、组合兼容 |
| oh-my-dsh | DSH Distribution 层探索 | 很早期 | 官方 RC1 release 已主动引用社区 dsh-plugin-upgrade-skill | 持续维护、0.1.3 migration 覆盖、真实降复杂度能力 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | 复用 Claude Code skills/commands/rules/agents/hooks/MCP | 很早期 | 已进入插件发现生态 | 0.1.3-alpha.1、语义差异、版本漂移 |
| BrowserSkill | 浏览器登录态 + browser tools / 人工接管 | 可尝鲜 | 已关注 record-safe observation | 权限、安全、0.1.3 Remote/Session lifecycle |
| SSH / Remote / Ops | DSH 向通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | RC1 Remote API 统一；0.1.3-alpha.1 所有出站请求开始遵循 HTTP(S)/ALL_PROXY/NO_PROXY | 凭证、安全、审计、代理环境语义、最小权限、第三方 Remote extension seam |
| Memory / Soul | 跨 Workspace Memory / 身份 / 检索注入 | 实验性 | token budget、RRF、压缩、防 context explosion | Session v2 迁移、误记、污染、跨项目泄露、成本 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | Web 工作台基础设施 | 可日常尝鲜 | RC1 前后出现 settings/client loader 兼容问题 | **0.1.3-alpha.1** Session v2 / Web contract；Session branching、多工作区 |
| dsh-TUI | 正从终端客户端向可承载第三方插件的前端 Runtime 演进 | 可日常尝鲜 | 公开 API/test-utils、toast、permission preset、runtime theme plugin | **0.1.3-alpha.1**、插件接缝稳定性、SessionHandle、多 Agent 长期运行 |
| dsh-web-ui | Remote/Git/SSH/Doctor/Task UI 综合增强 | 可尝鲜 | Remote、Recovery、Doctor 持续增强 | 0.1.3-alpha.1、复杂度、安全 |
| Desktop wrappers | 官方 Harness/Web 的桌面产品层 | 可尝鲜 | 维护树开始精确 pin 依赖并做 dependency/capability artifacts 门禁 | 0.1.3 Session v2/SessionHandle、插件隔离、迁移预检、长期 contract 稳定性 |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS、配对、证书 pinning、LAN discovery | 0.1.3、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | Context reclamation / durable working-state；把保存状态与安全回收旧 Context 分开 | 很新；0.1.3 SessionHandle / Session v2、workspace 隔离 |
| dsh-subagent-contract | 重读父/子 Session 日志验证 durable parent/depth/admission/follow-up/report | Research preview；重点验证 0.1.3 `send_message` steer/cold recovery、Session v2、Agent Teams 与 one-shot 子 Agent 互操作 |
| dsh-provider-passport | 对自建 / 企业 OpenAI-compatible Provider 做 request-dialect 预检，并映射到 Harness compat 字段后真实 runtime 验证与回滚 | Preview；0.1.3 custom-model discovery、真实网关样本量、误判、最小变更与回滚边界 |
| dsh-plugin-hub / dsh-mcp-manager | Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` | 0.1.3、安全、与 dsh-mcp-lazy 的 Context 成本对比 |
| dsh-auto-maintenance | 插件自检、快照、失败回滚、rescue | 权限重；0.1.3 Session v2 迁移是重要真实检验面 |

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
| 2026-09-02 | 0.1.2-alpha.5 | RC 前最后一轮高频 ABI/依赖兼容暴露；出现旧 projection-cache 污染与公开 API 缺口案例 |
| 2026-09-03 | 0.1.2-rc.1 | 0.1.2 首个候选版本；Session 按需读取 API、双向 Subagent `send_message`、Remote API 统一、Session 尾部自动修复等进入 RC 基线 |
| 2026-09-04 | RC1 首日真实升级验证 | 出现官方内置包旧依赖、Session service-shape mismatch、Provider settings 注册失效，以及 Agent Teams × foreground one-shot Subagent 互操作失败；RC gate 从 clean boot 扩展到原地升级与组合 Runtime |
| **2026-09-04** | **0.1.3-alpha.1** | **新开发线开启：SessionHandle + async agentLoop + 跨进程 Session lock + Session format v2；修复空 tool-call ID/name 污染，并强化 Agent Team cold-recovery 消息语义；同时存在已知历史 Session 加载性能回退** |

## 当前长期主线

1. **动态能力暴露**：Anchoring、Tool Schema、MCP Lazy、Context/Persona Router。
2. **多 Agent 治理**：Agent Teams、Subagent durable relation、`send_message` steer/cold recovery、foreground/background/continuable 模式互操作、nested waiting/continuation、执行前审批、usage/成本可观察性。
3. **版本/兼容双线**：稳定候选基线 **0.1.2-rc.1** + 最新开发基线 **0.1.3-alpha.1**；重点验证 SessionHandle / Session v2、clean install + 原地升级、Plugin ABI、Provider/Remote contract。
4. **插件生命周期**：Market、Doctor、rollback、diagnostics、供应链与 Profile/Distribution。
5. **前端 Runtime 平台化**：TUI/Web/Desktop 承担第三方插件 Runtime 与 Remote/Session 生命周期职责。

## 现在最值得长期盯的对象

1. Anchored Standard / 动态 Tool Schema
2. dsh-routing-suite
3. dsh-mcp-lazy
4. 官方 Agent Teams vs dsh-agent-teams / `send_message` steer / one-shot interoperability / nested continuation
5. dsh-context
6. **0.1.3-alpha.1 SessionHandle / Session v2 / cross-process lock / compatibility**
7. dsh-market + Doctor / Compatibility
8. dsh-TUI / better-sidebar / Web UI / Desktop Runtime

## 维护规则

- 每天只把**实质增量**写进 `history/YYYY-MM.md`。
- `RADAR.md` 只在当前判断变化时更新。
- 新项目先 Candidate，持续有真实代码 / Release / 兼容验证后再升 P1/P0。
- 普通 Fork、纯换皮、一次性 Demo、Star 波动默认过滤。
- 长期无进展或被官方取代的项目进入 Archive，但历史不删除。
- 当前只观察，不安装 / 下载 / 运行第三方插件。