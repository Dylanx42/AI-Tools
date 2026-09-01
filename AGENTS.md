# AGENTS.md

## Repository purpose

This repository is a collection of small AI-assisted tools, automations, and long-running research/radar projects.

## Layout rules

- Every project lives under `projects/<project-slug>/`.
- Keep each project self-contained: source code, scripts, configs, project README, changelog, privacy/security notes, and project-specific assets belong inside that project directory.
- Do not place project-specific source files, build scripts, app metadata, or project documentation in the repository root.
- The repository root is reserved for repository-wide files such as `README.md`, `AGENTS.md`, `.gitignore`, and `.github/`.
- Shared GitHub Actions workflows live in `.github/workflows/` and should use path filters so unrelated projects do not trigger each other's CI.
- New projects should use a stable lowercase ASCII slug with hyphens, for example `projects/my-new-tool/`.

## Before changing files

1. Read the root `README.md` and the target project's `README.md`. For a documentation-only Phase 0 project that does not have its final README yet, read `README_PHASE0.md` instead.
2. Run `git status --short` and inspect any existing uncommitted work before editing.
3. Do not delete, overwrite, or reset unrelated local changes.
4. If the working tree is clean and the task is based on `main`, sync safely before editing:
   - `git fetch origin`
   - `git pull --rebase origin main`
5. Never use force-push for normal maintenance unless the user explicitly requests it.

## Commit and push discipline

- Keep one logical project change per commit when practical.
- Stage only the target project and any intentionally changed repository-wide files.
- Before committing, run `git diff --cached --check` and inspect `git status`.
- Before pushing, fetch again. If remote `main` moved, rebase the local work onto the latest `origin/main`, resolve conflicts, rerun validation, then push.
- Do not solve a non-fast-forward rejection by force-pushing over remote work.
- Finish with a clean working tree unless the user explicitly asked to leave local changes uncommitted.

## Project-specific guidance

### `projects/codex-quota-bar/`

- Native macOS Objective-C menu bar utility.
- Run commands from inside `projects/codex-quota-bar/` unless a command explicitly uses a repository-root path.
- Validate after changes with:
  - `plutil -lint Info.plist`
  - `./build.sh`
  - `codesign --verify --deep --strict --verbose=2 "dist/Codex 额度栏.app"`
- Keep generated `.build/` and `dist/` content untracked.

### `projects/deepseek-harness-radar/`

- Documentation/data project maintained by a ChatGPT scheduled workflow.
- `RADAR.md` is the current-state baseline.
- `history/YYYY-MM.md` stores chronological deltas.
- Preserve the existing observation-only policy described in that project's README.

### `projects/racktool/`

- RackTool is an active V0.5 code project; V0.1 through V0.5 automated gates and remaining manual
  validation are recorded under `projects/racktool/docs/gates/`.
- Read `projects/racktool/AGENTS.md` before any RackTool task; its requirements, architecture documents, roadmap, and accepted ADRs are the project contract.
- `README_PHASE0.md` is retained as historical bootstrap context; `projects/racktool/README.md` is the
  current project entry point.
- One private real rack workbook contains two materially different Sheet-scoped Golden layouts with
  expected results and source Hashes. The asset-inventory workbook is reconciliation evidence, not a
  second rack-layout Golden. Keep all private business content Git-ignored, and never substitute screenshots
  or synthetic fixtures for real Golden evidence.
- Keep all RackTool-specific files under `projects/racktool/` and do not create a nested Git repository.

## Adding a new project

Create `projects/<project-slug>/README.md` first, then keep all project-specific files beneath that directory. A documentation-only Phase 0 package may temporarily provide `README_PHASE0.md` when its accepted project contract explicitly defers the final README to the first development task. Update the root README project table when the new project becomes part of the maintained collection.
