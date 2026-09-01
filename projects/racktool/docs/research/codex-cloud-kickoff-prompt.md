# Codex Cloud 开工提示词

> 历史说明：本文件保留 V0.1 开工时使用的提示词，不代表当前项目状态；其中 Golden Sample
> follow-up 已由后续私有验收完成。当前状态见 `../../README.md` 与
> `../gates/V0.5-integrated-audit.md`。

将下面整段作为 RackTool 第一个 Codex Cloud 开发任务使用。

**前置条件：** 本地 Codex 已经按照 `codex-local-bootstrap-prompt.md` 将 Phase 0 文档完整提交并 push 到 `AI-Tools` 远端仓库。Codex Cloud 中必须已经能够看到 `projects/racktool/AGENTS.md` 与 `projects/racktool/docs/`。如果这些文件不存在或不完整，请停止，不要重新猜测或重建项目约束。

---

You are starting development of the `RackTool` project inside my `AI-Tools` monorepo.

## Repository scope

- Work **only** inside `/projects/racktool` unless I explicitly ask otherwise.
- Do not modify sibling projects under `/AI-Tools`.
- Do not run `git init` inside `/projects/racktool`; the parent repository is already the Git repository.

## Mandatory reading before coding

Read these files in order and treat them as the project contract:

1. `projects/racktool/AGENTS.md`
2. `projects/racktool/docs/product/requirements.md`
3. `projects/racktool/docs/research/background-research.md`
4. `projects/racktool/docs/architecture/overview.md`
5. `projects/racktool/docs/architecture/data-model.md`
6. `projects/racktool/docs/architecture/profile-design.md`
7. `projects/racktool/docs/roadmap/ROADMAP.md`
8. all accepted ADRs under `projects/racktool/docs/decisions/`

If you find contradictions, stop and report them instead of silently choosing a different architecture.

## Goal of this first task

Bootstrap RackTool as a clean Python project and implement the **safe foundation of V0.1 Reader**, but do not jump ahead into GUI, Skill, write-back, AI integration, or V0.3+ features.

### 1. Create/verify project skeleton

Create a maintainable structure consistent with the architecture docs, for example:

```text
projects/racktool/
├── pyproject.toml
├── README.md
├── src/racktool/
│   ├── __init__.py
│   ├── models/
│   ├── core/
│   ├── profiles/
│   └── cli/
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

Do not create empty folders or placeholder modules unless they have a concrete near-term purpose.

### 2. Define the first stable domain models

Implement the minimum practical versions of:

- Rack
- Device
- Placement
- CellRange
- SourceMapping only if needed by the Reader foundation
- analysis/candidate types as needed

Requirements:

- typed;
- serializable to deterministic JSON-friendly structures;
- no dependency on PySide/GUI;
- no dependency on Agent/cloud APIs;
- no direct openpyxl objects stored in domain entities.

Do not over-engineer persistence yet.

### 3. Implement Workbook Scanner only

Implement a deterministic `.xlsx` scanner using `openpyxl` that can extract workbook structure needed by later detection logic:

- sheet names;
- used ranges/dimensions;
- non-empty cell values;
- merged ranges;
- row heights;
- column widths;
- enough style metadata/signatures for later rack/device detection, without trying to perfectly clone Excel formatting.

The scanner must not assume all racks are 48U.

### 4. Implement a minimal CLI entry point

Add a command such as:

```bash
racktool inspect <file.xlsx>
```

or an equivalent clear command.

For this first task, it should output a deterministic JSON/summary of workbook structure, not pretend that full Rack/U detection is already solved.

### 5. Tests

Because the real Golden Sample `.xlsx` files are not in the repository yet:

- create small synthetic workbooks inside tests using `openpyxl`;
- include at least:
  - one single-U-axis rack-like layout;
  - one dual-U-axis layout;
  - merged cells representing 1U/2U/multi-U devices;
  - non-48U height example;
  - Chinese text / multi-line cell text;
- test scanner output deterministically.

Do **not** invent expected results for the user's real screenshots. At the time of this historical prompt,
real Golden evidence was still outstanding; that gap was later fulfilled with privately retained workbook evidence
and must never be replaced by synthetic fixtures.

### 6. Engineering quality

- Use `pathlib`.
- Keep dependencies minimal.
- Add pytest configuration.
- Add type hints.
- Avoid Windows-only APIs and Office COM.
- Do not add Docker.
- Do not add SQLite until a task actually needs persistence.
- Do not add PySide6 in this task.

### 7. README

Create a concise project README that states:

- what RackTool is;
- current development status;
- supported scope (`.xlsx`, cells, merged cells);
- what is intentionally not supported yet;
- development/test commands;
- link to the architecture docs.

## Acceptance criteria

This task is complete only if:

1. all changes are under `/projects/racktool`;
2. `pytest` passes;
3. the package can be installed in editable mode;
4. the CLI can inspect a synthetic/test `.xlsx` and emit deterministic output;
5. the code follows the documented dependency boundaries;
6. no GUI/Agent/write-back feature is prematurely introduced;
7. the final report includes:
   - files changed;
   - commands/tests run and results;
   - architecture decisions you followed;
   - known limitations;
   - exact next recommended task for V0.1.

Before finishing, review `git diff` and remove unrelated or speculative changes.
