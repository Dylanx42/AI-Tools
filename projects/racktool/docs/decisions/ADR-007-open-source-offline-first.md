# ADR-007: 项目定位为开源/内部共享、Offline-first 工具

- Status: Accepted
- Date: 2026-08

## Context

项目不是独立商业软件，主要目标是自己和公司同事使用，并可开放源码分享。

## Decision

V1 不建设：

- 账号系统；
- SaaS；
- 云数据库；
- 计费；
- 多租户；
- 授权码体系。

本地 APP 应在无网络、无 Agent 情况下正常工作。

许可证（MIT/Apache-2.0）在公开发布前再最终确定。

## Consequences

项目可以把资源集中在：

- Parser 准确性；
- Mapping 稳定性；
- Safe Sync；
- GUI 可用性；
- Profile/Skill 可扩展性。
