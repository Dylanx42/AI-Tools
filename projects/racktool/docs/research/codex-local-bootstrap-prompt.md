# Codex 本地接入与落库提示词

把下面整段交给**本地 Codex**。同时把 `RackTool-Phase0-Docs.zip` 提供给它，并确保它能够访问你本地已经 clone 的 `AI-Tools` 仓库。

---

You are preparing the `RackTool` project for development inside my existing local `AI-Tools` Git repository.

I have provided a Phase 0 documentation package named `RackTool-Phase0-Docs.zip`.

Your job in this task is to **integrate this package into the existing monorepo safely and push the Phase 0 baseline to the configured remote repository**. Do not start implementing RackTool business features in this task.

## 1. Locate and verify the repository

- Locate my existing local `AI-Tools` repository.
- Use Git commands such as `git rev-parse --show-toplevel`, `git remote -v`, `git branch --show-current`, and `git status` to verify the repository before changing files.
- The existing `AI-Tools` repository must remain the only Git repository.
- **Do not run `git init` inside `projects/racktool/`.**
- Do not create a nested repository.
- Do not modify sibling projects under `AI-Tools`.

If the working tree contains unrelated uncommitted changes that could be affected, stop and report them instead of overwriting or cleaning them.

## 2. Integrate the Phase 0 package

Extract the supplied archive and copy/merge its `RackTool/` directory into:

```text
<AI-Tools repository root>/projects/racktool/
```

Expected documentation baseline includes at least:

```text
projects/racktool/
├── AGENTS.md
├── README_PHASE0.md
└── docs/
    ├── product/requirements.md
    ├── research/
    │   ├── background-research.md
    │   ├── original-conversation.md
    │   ├── codex-local-bootstrap-prompt.md
    │   └── codex-cloud-kickoff-prompt.md
    ├── architecture/
    │   ├── overview.md
    │   ├── data-model.md
    │   └── profile-design.md
    ├── roadmap/ROADMAP.md
    └── decisions/
```

Rules:

- Preserve the supplied document contents unless a path/reference must be adjusted to fit the actual repository layout.
- If `projects/racktool/` already exists, merge carefully; do not blindly overwrite existing unrelated code or documents.
- Do not invent application code, GUI code, Skill code, database code, or parser code in this bootstrap task.
- Do not rename `README_PHASE0.md` to the future project `README.md`; the actual project README will be created during the first development task.

## 3. Validate the documentation baseline

Before committing:

- verify all expected Markdown files exist under `projects/racktool/`;
- verify internal paths in `AGENTS.md` and the kickoff prompts are correct relative to `projects/racktool/`;
- run `git status` and `git diff --check`;
- review the diff and confirm that changes are limited to `projects/racktool/` plus any intentionally updated repository index.

Do not make speculative architecture changes. The supplied Phase 0 documents are the current project contract.

## 4. Commit and push

Follow the repository's existing branch/PR policy if one exists.

If no policy exists:

- create a dedicated branch such as `racktool/phase0-bootstrap` rather than force-pushing or rewriting history;
- commit only the RackTool Phase 0 baseline;
- use a clear commit message such as:

```text
docs(racktool): add phase 0 project foundation
```

- push the branch to the existing remote repository;
- never use `--force`.

If authentication or permissions prevent pushing, leave the local commit intact and report the exact blocker and the exact command I should run next.

## 5. Final report

At the end, report:

1. detected repository root;
2. active branch;
3. remote repository used;
4. files added/changed under `projects/racktool/`;
5. validation commands run and their results;
6. commit hash if created;
7. whether push succeeded and the remote branch name;
8. whether the repository is now ready for the Codex Cloud kickoff task.

Stop after the Phase 0 baseline is safely integrated and pushed. Do not start V0.1 implementation in this task.
