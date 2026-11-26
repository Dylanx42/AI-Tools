---
name: racktool-allinluna
description: Use All in Luna to coordinate RackTool implementation and verification with RackTool-specific task sizing, GPT-6 Luna routing, RackCore boundaries, and acceptance gates.
---

# RackTool 专用 All in Luna 工作策略

这是全局 All in Luna Skill 的 RackTool 项目覆盖规则，不替换或修改全局插件。通用运行协议仍适用于确实启动的 Run；本文件负责让任务拆分、模型强度和验收标准贴合 RackTool。

## 何时使用

- 任何会修改 RackTool 代码、测试、项目文档、构建或打包配置的任务，默认经 All in Luna 协调。
- 单纯解释功能、讨论规划或只读查看状态时，直接回答即可，不为形式创建 Run。
- 一个用户目标默认对应一个顶层 Task。把检查、实现、回归和收口作为该 Task 内的步骤；不要为了套模板而按文件、角色或流程阶段创建多个并行 Task。
- 默认一个实现 Lane。只有工作确实相互独立、输入输出明确且不会同时改同一文件或同一核心规则时，才增加只读审查或独立工作 Lane。

## 模型和推理强度

- RackTool 项目任务首选 `gpt-6-luna`。推理强度按风险分配：
  - `low`：纯格式、文档拼写、小范围机械整理；
  - `medium`：边界清楚的常规功能、UI 文案和对应测试；
  - `high`：Reader/Profile、身份与 Mapping、RackCore 冲突判断、Safe Sync、OOXML/Excel 保真、数据迁移或回滚；
  - `xhigh`：涉及多个核心子系统、相互冲突的 ADR/实现证据或需要重新评估架构的变更；
  - `max`：仅在确有高影响不确定性且任务明确授权时使用。
- 配置中的模型名不证明实际路由。保留 requested / resolved / actual 的区别；实际模型证据缺失时标记 `unverified` / `unresolved`，不可把请求值写成已使用模型。
- 若指定模型无法路由，不得悄悄切换成别的模型并声称完成。对于安全敏感的实现，先停在模型路由缺口并向用户说明；其他工作是否改走当前模型也必须符合用户当时的授权。

## RackTool 实施边界

- 开工先核对当前分支、工作区改动和项目现状，再按 RackTool AGENTS.md 阅读需求、背景研究、架构、路线图和相关 ADR。若主线移动，先审查双方提交与重叠文件，再用不丢弃任何一侧的方式整合。
- RackCore 是唯一确定性核心。GUI、CLI、Skill 只能调用 RackCore，不能复制识别、位置、冲突或写表规则；不要把 All in Luna、Agent 或云 API 加进 RackCore 或离线 GUI。
- 所有源 XLSX 写操作必须走已验证的 Safe Sync 流程。模型不得直接改工作簿；读真实样本时只在本机处理，不把客户工作簿内容复制到 Lane、远端提示或提交记录。
- 修 Bug 要先按用户实际文件、当前持久项目状态和实际 UI 调用链复现；区分“目标确实被占用/不支持”和“系统误判”。修复后增加能在自动化环境稳定重现的回归测试。
- Synthetic fixture 仅验证规则，不是 Golden Sample。真实私有样本仍留在 Git 忽略目录，不能为凑覆盖率伪装真实样本或提交业务数据。

## RackTool 验收

- 先运行针对性测试，再运行项目要求的完整 `pytest`；已有 lint/type-check 时同时运行 `ruff check .` 和 `mypy src`。按改动补 CLI、Safe Sync、集成和 headless GUI 验证。
- 通过自动化不等于 V0.1–V0.5 全部 PASS。Microsoft Excel/WPS 实机打开、macOS 人工 GUI 检查、Windows GUI 检查等未实际完成的事项必须标为 `MANUAL VALIDATION PENDING`。
- All in Luna 的 Run/Lane 状态只是编排证据，不是业务 Gate、人工验收或文件安全证明。Codex 必须审查关键差异和测试结果后再给 Gate 结论。
- Run 数据库存放在项目目录之外的稳定位置，避免把运行数据库、临时导出、调试工作簿或其他生成物散落进仓库；Run/Evidence 未经验证持久归档前不得清理。

## 后续产品顺序

优先修好并验证现有移动/冲突链路；之后在 RackCore 建立设备新增、删除和批量操作的可验证接口，再补 JSON/CLI 合同；随后设计机柜排布生成接口；最后让自然语言 Skill 调用这些接口。GUI 保持为本地离线辅助工具，不作为核心业务逻辑或未来 Agent 的依赖。
