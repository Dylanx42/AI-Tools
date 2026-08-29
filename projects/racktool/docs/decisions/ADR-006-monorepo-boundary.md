# ADR-006: RackTool 作为 AI-Tools monorepo 内独立项目目录

- Status: Accepted
- Date: 2026-08

## Context

用户计划将 RackTool 放在远端 `AI-Tools` 主仓库中，通过 Codex Cloud 开发。

## Decision

目录：

```text
AI-Tools/
└── projects/
    └── racktool/
```

RackTool 不再单独 `git init`。

Codex Cloud 任务默认：

- 只工作在 `/projects/racktool`；
- 不修改兄弟项目；
- 项目级规则放 `projects/racktool/AGENTS.md`；
- 项目设计知识放 `projects/racktool/docs/`。

## Consequences

优点：

- 统一管理 AI 工具；
- 易共享公共 CI/规范；
- Codex Cloud 直接连接一个仓库即可。

风险：

- Agent 可能误改兄弟项目，因此必须通过 AGENTS 和任务提示词重复限定 scope。
