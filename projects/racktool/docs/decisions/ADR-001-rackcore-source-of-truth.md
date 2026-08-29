# ADR-001: RackCore 作为唯一核心能力层

- Status: Accepted
- Date: 2026-08

## Context

RackTool 计划同时提供：

- 本地 GUI；
- CLI；
- Agent Skill。

如果三种入口分别实现 Excel 解析、Mapping 和同步逻辑，会迅速分叉，修复一个 Bug 需要维护多套实现。

## Decision

建立唯一 Python 核心层 RackCore：

- Parser；
- Mapping；
- Validator；
- Sync；
- Backup；
- Profile；
- 核心数据模型。

GUI、CLI、Skill 都只能调用 RackCore。

RackCore 不依赖 GUI、Agent、ChatGPT、Codex Runtime 或云 API。

## Consequences

优点：

- 单一逻辑源；
- 测试集中；
- Bug 修一次；
- 本地离线可用；
- Skill 与 APP 行为一致。

代价：

- 需要更明确的模块边界；
- UI 必须接受 Core API 的约束，而不是随意直接操作 Excel。
