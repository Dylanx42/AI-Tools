# Anchored Standard 回顾：从“能力解锁”到 Harness 研究基线

> 整理日期：2026-09-16  
> 目的：把 2026-08～09 对 `xiaobright/dsh-anchored-standard` 的连续观察收敛成一份长期可复用的判断，避免继续被早期 98/99/99、`We need` 轨迹或单次复现牵着走。

## 一句话结论

**Anchored Standard 现在最有价值的身份，不是“把 DeepSeek 解锁到 98/99 的生产增强插件”，而是一个研究 Harness / Agent Scaffold 如何改变模型行为的高价值实验基线。**

截至 2026-09 中旬，持续观察已经把几个问题分开了：

1. **trajectory 可以被稳定影响，不等于最终 Ability 会稳定大幅提升；**
2. **API-visible Tool Schema、首请求 Context、Skills/AGENTS 注入、promotion 与工具发现方式，确实会改变模型行为；**
3. **历史 98/99/99 不能直接归因到当前 generic preset；**
4. **DSH 本身的 Session / Subagent / Compaction / Migration / Runtime 可靠性，已经成为比“首轮能不能锚定”更现实的工程瓶颈；**
5. **旧 V4 Pro 已退出当前主线，下一阶段应把 V4.1 Flash 和后续模型建立独立 cohort，重新做同 Harness A/B。**

---

## 1. 最初为什么值得关注

Anchored Standard 最早吸引人的地方，是同一个 DeepSeek V4 Pro 在不同 Harness / Tool Schema 下出现非常大的行为和 benchmark 差异。

早期核心假设可以概括为：

> 模型权重没有变化，但第一轮 API 请求暴露给模型的 Tool Schema、System Prompt、自动注入 Context 等条件，可能让模型进入不同的 Agent trajectory。

最典型的现象是：

- Minimal 风格的首请求更容易出现 `We need... / Let's...`；
- Standard 大工具面更容易出现另一类规划轨迹；
- 真实 callable Tool Schema 的效果明显强于“把工具名字写进普通文本”；
- 因此问题更像 **training-scaffold / Harness alignment**，而不是一句神秘 Prompt 或 CoT 咒语。

这个方向后来被多轮消融继续支持，因此 **“模型会被 Harness 条件化”** 这条主结论仍然有研究价值。

---

## 2. 98/99/99 为什么不能再当成核心卖点

持续复现后，早期最夸张的分数需要明显降权。

### 关键修正

- 历史 98/99/99 来自更早期、不同 composition 的实现；
- 当前 generic Anchored preset 的 tool/bootstrap/promotion 组合已经发生过明显变化；
- 因此不能把历史高分直接写成“当前 Anchored Standard = 98/99”；
- 多环境独立复现里出现过明显更低的结果；
- 后续一些统计只支持小幅均值差，而且置信区间并不能稳定排除无增益。

所以现在应明确区分：

| 证据 | 当前判断 |
|---|---|
| trajectory / reasoning 风格被锚定 | **证据较强** |
| Tool Schema / Context 注入能改变模型行为 | **证据较强** |
| 当前 preset 可稳定带来巨大 Ability 提升 | **证据不足** |
| 历史 98/99/99 可跨环境稳定复现 | **目前不成立** |

这也是后续所有 Radar 记录必须坚持的原则：**不要把 trajectory 指纹当作 Ability 指标。**

---

## 3. 真正沉淀下来的机制结论

相比具体分数，项目留下的 Harness 设计经验更值得保留。

### 3.1 首请求的真实 Tool Schema 很重要

最稳定的观察之一是：**模型看到的 API-visible callable tools 本身会影响 trajectory。**

这意味着：

- Tool Schema 不是单纯“功能列表”；
- 工具数量、组合、语义都可能改变推理策略；
- 仅把工具说明写进 System Prompt，不能等价替代真实 Tool Schema；
- “少工具”也不是充分条件，具体组合比纯数量更重要。

### 3.2 首轮自动 Context 注入应尽量克制

AGENTS.md / CLAUDE.md 摘要、Skills catalog、长系统说明等，如果在第一请求直接注入，曾多次观察到会改变或破坏预期 trajectory。

由此形成的更一般原则是：

> **首轮保持稳定、精简的真实请求面；需要的信息在后续按需发现，而不是一开始全部灌入。**

这个原则不只适用于 Anchored，也值得迁移到 Codex、OpenCode、自建 Agent 等其他 Harness。

### 3.3 Promotion 不应该等于“一次性恢复全部工具”

项目后期逐渐从：

`Minimal → 全量 Standard tools`

转向：

`Minimal → 小型 resident catalog → 重工具按需 unlock`

原因是完整工具目录本身也可能重新改变 trajectory，并增加 Schema/context 成本。

这条经验可以抽象成：

> **Capability discovery 与 capability residency 分离。**

Agent 可以“知道如何发现工具”，不代表所有工具都应该永久常驻在每轮 API 请求里。

### 3.4 `max_tokens` 不是核心开关

早期曾把首请求 1024 token cap 当成重要 trigger，但后续实验明显削弱了这个结论：

- 不设 cap 仍可以出现稳定 anchoring；
- 过小的 cap 反而可能因为截断 reasoning / continuation 放大 drift；
- 不同 Harness/profile 的 `maxTokens` 配置也不一定真正等价于 wire 上的 provider payload。

因此目前优先级应理解为：

**真实 Tool Schema / 首请求 Context / provider envelope > 单纯调 `max_tokens`。**

### 3.5 不要用 `We need / Let's` 当能力指标

这是整个观察过程中最重要的“去魅”之一。

`We need / Let's / Let me` 只能作为 trajectory fingerprint，最多帮助判断模型进入了哪类行为模式；它不能直接证明：

- 代码更正确；
- 漏项更少；
- benchmark 更高；
- 长任务更可靠。

真正的 Ability 仍然必须看 paired A/B、任务结果、测试通过率、错误率、人工纠错量等硬指标。

---

## 4. 后来为什么越来越不适合直接当生产插件

随着观察深入，主要风险已经从“Anchored 是否能触发正确轨迹”转移到 **DSH Runtime / Session substrate 是否足够可靠**。

持续出现过的风险类型包括：

- Session resume / migration 兼容问题；
- compaction 后状态与上下文恢复问题；
- Subagent / parent session 的消息与 provider 继承问题；
- persistent bash / PTY / heredoc / workdir 边界；
- duplicate event / seq gap / writer-reader invariant 不一致；
- 旧 Session V2/V3 migration fail-closed；
- 第三方插件 durable event metadata 导致历史不可加载；
- search/index 受单个坏 Session 放大影响；
- Session / storage 可能出现 silent truncation 或 silent false negative；
- DSH 版本迭代导致 persona、Session API、Agent/Inbox、plugin ABI 等持续 breaking。

这些问题有一个共同点：

> **即使模型本身很聪明，Harness 给它的世界状态如果不完整、错误或不可恢复，最终 Agent 仍然不可靠。**

对于真实工程工作流，这比首轮 CoT 轨迹更关键。

---

## 5. V4 Pro 退场后，研究目标已经变化

2026-09 中旬以后，旧 V4 Pro 已不再适合作为未来主线 cohort。

因此后续不能再把：

- 旧 V4 Pro；
- V4 Flash；
- V4.1 Flash；
- 后续模型

混在一起讨论“Anchored 是否有效”。

### 下一阶段真正值得做的实验

固定模型、固定版本、固定任务、固定 provider 后，做：

- V4.1 Flash Standard
- V4.1 Flash Minimal
- V4.1 Flash Anchored-style

的 **同 Harness / 同 benchmark paired A/B**。

优先看：

- 最终任务成功率；
- 测试通过率；
- 漏项 / 错误数；
- 人工纠错次数；
- token / latency / tool-call 成本；
- compaction / subagent / long-session 后是否退化。

不要再以 CoT 文风作为主要判断依据。

---

## 6. 对真实工程 Agent 工作流还能起什么作用

### 仍然有价值

**A. Harness A/B 实验基线**  
用于比较不同 Tool Schema、Context policy、promotion 策略、Skills 注入方式。

**B. Agent 架构设计参考**  
尤其是：

- small bootstrap surface；
- Context 延迟注入；
- resident catalog + on-demand discovery；
- tool visibility 与 SDK/context richness 分离；
- compaction / resume / subagent 需要显式验证；
- provider payload 必须实际观测，不能只相信 UI/Profile 配置。

**C. 新模型 scaffold sensitivity 的对照组**  
即使 Anchored 本体冻结，它仍然可以作为后续 V4.1 Flash / 新模型的历史 control design。

### 不再建议承担的角色

**不建议把它包装成“生产环境自动提升 DeepSeek 能力的插件”。**

原因不是 Anchored 的所有机制都错了，而是：

1. 巨大 Ability 增益缺乏稳定复现；
2. 原目标模型已经变化；
3. DSH 长生命周期可靠性仍处快速演化期；
4. 真正生产场景更关心 session correctness、工具 observation 正确性、恢复能力和审计，而不是首轮 trajectory 是否漂亮。

---

## 7. 当前 Radar 定位

从现在开始，Anchored Standard 应从“待部署能力增强插件”调整为：

> **Harness / Agent Scaffold 历史研究基线。**

后续只有以下事件值得重新提高优先级：

1. V4.1 Flash / 后续模型出现同 Harness 的完整 paired A/B；
2. 有跨 repo / 跨项目 benchmark 证明 Anchored-style scaffold 带来稳定净增益；
3. 机制被 Codex / OpenCode / Pi / DSH 官方或其他成熟 Runtime 吸收；
4. 出现更可靠的独立实现，保留小 Tool Surface / 延迟 Context / 按需 discovery，但摆脱当前 DSH 长 Session 风险；
5. DSH Session / Compaction / Subagent / Migration 进入真正可长期运行的稳定阶段。

否则，普通 Star、Fork、CoT 截图、单次 session 或小 UI 更新都不值得重新提高关注级别。

---

## 8. 给当前工作流的最终建议

如果以后要重新测试，不要直接拿生产项目试。

应使用**有标准答案、可回放的真实工程样本**做隔离 A/B，例如：

- 多设备配置审计；
- VLAN / VRF / ACL / NAT / 路由一致性检查；
- 配置与表格互相校验；
- Python 自动化脚本修改 + 测试；
- 多文件项目目录中的信息抽取、修改和验证。

只比较结果：

**漏项、错误、测试通过率、人工纠错次数、完成成本。**

如果 Anchored-style 不能在这些指标上稳定赢 Standard / Minimal，就没有必要因为 trajectory 更“像高手”而保留它。

---

## 当前结论

**Anchored Standard 本体：保留观察，退出“生产候选”主线。**  
**Anchored 留下的 Harness 机制：继续作为 P0 研究方向。**  
**后续模型主线：转向 V4.1 Flash / 后续模型的同 Harness paired A/B。**  
**工程主线：优先关注 DSH Runtime / Session / Compaction / Subagent 的正确性与长期可靠性。**
