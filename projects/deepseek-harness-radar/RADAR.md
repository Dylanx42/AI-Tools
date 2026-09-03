# DeepSeek Harness Ecosystem Radar

> **用途**：长期跟踪 DeepSeek Harness 官方与插件生态；本文件只维护“当前状态”，每日历史看 `history/YYYY-MM.md`。  
> **当前策略**：只观察 / 比较 / 记录，不安装、下载或运行第三方插件。  
> **最后整理**：2026-09-03  
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
| dsh-mcp-lazy | MCP 工具按需暴露，降低常驻 Schema | 可尝鲜 | 多版 DSH 已有验证 | **0.1.2-rc.1** 兼容、激活准确率、与 MCP Manager 对比 |
| dsh-context | 多 Agent Context / 拓扑可观察层 | 可日常尝鲜 | 0.38.x 已处理早期 0.1.2 projection contract 变化 | **0.1.2-rc.1** Session/Chat/projection 验证；是否成为标准观测层 |
| Minimal Harness / byte-stable prompt | 少工具、稳定前缀、压缩输出降低 Harness 干扰 | 实验性 | identity drift 暴露极简 persona 的行为边界 | 可复现 benchmark；极简与身份/约束锚定平衡 |

## 🔥 P0｜Agent / Runtime

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 Agent Teams / Subagent Runtime | 已进入官方 experimental 孵化；0.1.2-rc.1 正式增强可持续 Subagent 的双向通信 | 官方实验性 | **父 Agent 与 continuable Subagent 现在可通过 `send_message` 双向传递后续消息，取代单向 `report`**；alpha 阶段暴露的 nested waiting/continuation 正确性仍需 RC 实测 | RC1 下 waiting 可观察性、孙 Agent settle 后 manager 自动续跑、durable relation、消息有序性 |
| dsh-agent-teams | 社区较成熟的 Leader + Persistent Worker + staged approval，但 0.1.2 线暴露前端/Runtime ABI 风险 | 可尝鲜 / 需版本匹配 | 0.1.15 已完成 alpha.2 实测验收；alpha.5 前后仍有 `registerContinuableSetup` 等 API 漂移报告 | **0.1.2-rc.1** 实际启动/业务验收、复杂任务稳定性、与官方 `send_message` 机制收敛程度 |
| Conductor / Agent orchestration | 多 Agent 编排、依赖与协调 | 实验性 | 官方 RC 已把双向 Subagent follow-up 纳入正式 0.1.2 变更，但嵌套等待/恢复仍是核心正确性问题 | 状态管理、等待/唤醒、故障恢复、是否与官方 Teams 合流 |
| iterate-plugin / 自治闭环 | plan → review → fix → verify → loop | 实验性 / 可尝鲜 | 已形成 dry-run/meta-review/自动停止思路 | 自动停止、错误累积、长期任务表现 |

## 👀 P1｜官方 DSH / Provider / Session

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| 官方 DSH 0.1.2 | **当前兼容基线已进入 `0.1.2-rc.1`**；这是 0.1.2 系列首个候选版本 | **RC** | 2026-09-03 发布 RC1：`Session.events` 被按需读取 API `seq` / `eventAt()` / `snapshotEvents()` 取代；`SessionSeq` 与 `SessionLogOffset` 强类型区分；移除 SQLite Session 后端；Remote API 统一；会话截断尾部可自动修复并告警 | RC1→stable；Session/projection、Client API/Remote、Plugin ABI、真实升级/恢复、Runtime reliability |
| 官方 DeepSeek Provider | Provider、多模态、附件能力持续收进主干 | RC 过渡 | RC1 默认向官方 DeepSeek 请求附带启用插件包名/版本（可关闭），并提供可选 Session 日志增量上传；自定义模型发现复用 Profile 请求头 | Gateway headers、request dialect、隐私/遥测边界、Vision、adapter capability negotiation |
| Codex / ChatGPT Provider | DSH 使用 Codex / ChatGPT 模型通道 | 早期实验 | RC1 子代理模型选择明确支持为 Claude Code、Codex 配置模型；社区 Codex provider 仍需逐版验收 | RC1 兼容、认证稳定性、模型目录、pi-ai 边界 |
| 多模型 Router | 按任务复杂度切模型 / Provider | 早期实验 | tier-router / routing-suite 等方向 | fallback、成本/质量数据、真实自动路由价值 |

## 👀 P1｜插件基础设施

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-market | 插件生命周期、诊断与可恢复更新基础设施 | 可日常使用 | 1.38.0 已实现失败更新精确恢复旧版本/commit + 回读验证 | **0.1.2-rc.1** compatibility matrix；Update API、供应链、恢复覆盖 |
| Compatibility / Upgrade Skills / upstream-radar | 0.1.2 已进入 RC，但“peer range 看起来兼容 ≠ Runtime ABI 真兼容”已被 alpha.5 升级案例明确验证 | 实验性→正在成型 | alpha.5 出现旧 `sessionProjectionCache` 被第三方插件依赖带入、导致旧会话全部无法加载的真实案例；同阶段还出现公开 API 缺口使 better-sidebar / agent-teams 等在当前主线加载失败；RC1 同时优化官方包 peer dependency | RC1 real-host boot gate；精确 contract surface、依赖树污染检测、旧 Session 升级测试、官方 Upgrade Skill |
| Doctor / Plugin Clinic | 插件故障诊断与恢复 | 可尝鲜 | 已形成启动失败→Session 辅助排障闭环 | RC1、自动修复边界、版本冲突、与 Market 整合 |
| Index / Profile / Distribution | Harness + Plugins 组合成 Agent Profile / Distribution | 早期 | 0.1.2 的 profile/core bundle 与 ABI 漂移强化 Profile contract 版本化需求 | 版本固定、预检、升级/回滚、组合兼容 |
| oh-my-dsh | DSH Distribution 层探索 | 很早期 | 能力发现、审批、Eval、版本固定、SHA、回滚 | 持续维护与真实降复杂度能力 |

## 👀 P1｜工具 / 生态兼容

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| dsh-cc-ecosystem | 复用 Claude Code skills/commands/rules/agents/hooks/MCP | 很早期 | 已进入插件发现生态 | RC1、语义差异、版本漂移 |
| BrowserSkill | 浏览器登录态 + browser tools / 人工接管 | 可尝鲜 | 已关注 record-safe observation | 权限、安全、RC1 BrowserAuth/Remote |
| SSH / Remote / Ops | DSH 向通用 Agent Runtime 延伸 | 分散 / 可尝鲜 | RC1 Remote 网关统一远程调用 API 与异常分发，旧 APIProxy 已迁移并移除 | 凭证、安全、审计、最小权限、第三方 Remote extension seam |
| Memory / Soul | 跨 Workspace Memory / 身份 / 检索注入 | 实验性 | token budget、RRF、压缩、防 context explosion | 误记、污染、跨项目泄露、成本 |

## 👀 P1｜Web / TUI / Desktop

| 项目 / 方向 | 当前判断 | 成熟度 | 最近实质变化 | 下一观察点 |
|---|---|---|---|---|
| DSH-better-sidebar | Web 工作台基础设施 | 可日常尝鲜 | alpha.5 前后出现 `settingsNamespace` API 缺失导致加载失败的公开兼容报告 | **RC1** 是否恢复/替代该 API；Session branching、多工作区 |
| dsh-TUI | 正从终端客户端向可承载第三方插件的前端 Runtime 演进 | 可日常尝鲜 | 公开 API/test-utils、toast、permission preset、runtime theme plugin | **RC1**、插件接缝稳定性、多 Agent 长期运行 |
| dsh-web-ui | Remote/Git/SSH/Doctor/Task UI 综合增强 | 可尝鲜 | Remote、Recovery、Doctor 持续增强 | RC1、复杂度、安全 |
| Desktop wrappers | 官方 Harness/Web 的桌面产品层 | 可尝鲜 | 维护树开始精确 pin 0.1.2 依赖并做 dependency/capability artifacts 门禁 | RC1 插件隔离、迁移预检、长期 contract 稳定性 |
| dsh-mobile | 移动端安全入口 | Alpha | HTTPS、配对、证书 pinning、LAN discovery | RC1、安全审计 |

## 🧪 Candidate

| 项目 / 方向 | 为什么进入候选 | 当前风险 / 下一观察点 |
|---|---|---|
| dsh-durable-context | Context reclamation / durable working-state；把保存状态与安全回收旧 Context 分开 | 很新；官方 compaction/session persistence 边界、workspace 隔离、RC1 |
| dsh-subagent-contract | 重读父/子 Session 日志验证 durable parent/depth/admission/follow-up/report | Research preview；重点验证 RC1 `send_message` 后的 nested waiting/continuation、更多失败形态、是否被官方吸收 |
| dsh-provider-passport | 对自建 / 企业 OpenAI-compatible Provider 做 request-dialect 预检，并映射到 Harness compat 字段后真实 runtime 验证与回滚 | Preview；RC1 真实网关样本量、误判、最小变更与回滚边界 |
| dsh-plugin-hub / dsh-mcp-manager | Workspace MCP 收敛为 `ws_mcp_search` / `ws_mcp_call` | RC1、安全、与 dsh-mcp-lazy 的 Context 成本对比 |
| dsh-auto-maintenance | 插件自检、快照、失败回滚、rescue | 权限重；RC1 迁移是重要真实检验面 |

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
| **2026-09-03** | **0.1.2-rc.1** | **0.1.2 首个候选版本；Session 按需读取 API、双向 Subagent `send_message`、Remote API 统一、Session 尾部自动修复等进入 RC 基线** |

## 当前长期主线

1. **动态能力暴露**：Anchoring、Tool Schema、MCP Lazy、Context/Persona Router。
2. **多 Agent 治理**：Agent Teams、Subagent durable relation、**RC1 双向 `send_message` + nested waiting/continuation**、执行前审批、任务/恢复正确性。
3. **0.1.2 RC 兼容窗口**：当前基线 **0.1.2-rc.1**；Upgrade Skill、contract-surface compatibility matrix、真实 Host boot gate、Session/projection、Client API/Remote 与 Plugin ABI。
4. **插件生命周期**：Market、Doctor、rollback、diagnostics、供应链与 Profile/Distribution。
5. **前端 Runtime 平台化**：TUI/Web/Desktop 承担第三方插件 Runtime 与 Remote/Session 生命周期职责。

## 现在最值得长期盯的对象

1. Anchored Standard / 动态 Tool Schema
2. dsh-routing-suite
3. dsh-mcp-lazy
4. 官方 Agent Teams vs dsh-agent-teams / RC1 `send_message` / nested continuation
5. dsh-context
6. **0.1.2-rc.1 compatibility / Upgrade Skill / Runtime reliability**
7. dsh-market + Doctor / Compatibility
8. dsh-TUI / better-sidebar / Web UI / Desktop Runtime

## 维护规则

- 每天只把**实质增量**写进 `history/YYYY-MM.md`。
- `RADAR.md` 只在当前判断变化时更新。
- 新项目先 Candidate，持续有真实代码 / Release / 兼容验证后再升 P1/P0。
- 普通 Fork、纯换皮、一次性 Demo、Star 波动默认过滤。
- 长期无进展或被官方取代的项目进入 Archive，但历史不删除。
- 当前只观察，不安装 / 下载 / 运行第三方插件。
