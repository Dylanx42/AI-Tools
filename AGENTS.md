# AGENTS.md

This file is the operating contract for any coding agent that maintains `Dylanx42/AI-Tools`.
The human owner does not do routine GitHub operations. If a task is about this repository, follow this file even when the current checkout happens to be on another branch.

## Source of truth

- Canonical remote: `https://github.com/Dylanx42/AI-Tools.git`
- Canonical branch: `origin/main`
- Human homepage: root `README.md`
- Agent contract: this file
- Project contract: `projects/<slug>/README.md`, plus that project's own `AGENTS.md` when it exists

Do not treat a local dirty worktree, a RackTool feature branch, or a previous Codex worktree as `main`.

## Default workflow

1. Identify exactly one target: one existing project, a new `projects/<slug>/`, or a repository-wide file such as `README.md` / `AGENTS.md` / `.gitignore` / `.github/`.
2. Read root `README.md`, this file, and the target project's README. For RackTool also read `projects/racktool/AGENTS.md`.
3. Inspect `git status --short` and `git worktree list`. Do not edit, reset, or commit unrelated local changes.
4. Start from a fresh checkout of latest `origin/main`. Preferred pattern:
   - `git fetch origin`
   - `git worktree add -b <type>/<slug> /tmp/ai-tools-<slug> origin/main`
5. Make the smallest change that satisfies the request.
6. Validate using the target project's commands below.
7. Commit only the intended files.
8. `git fetch origin` again. If `origin/main` moved, rebase onto it.
9. Push the feature branch and open a PR into `main`.
10. If the user asked to land the change, squash-merge that PR and delete the feature branch. Do not merge unrelated PRs.
11. Verify `origin/main` contains the expected files, then leave a clean result.

Never commit directly to `main` from a mixed local checkout. Never use force-push unless the user explicitly asks for that exact recovery.

## Branch and PR rules

- Branch names: `feat/<slug>`, `fix/<slug>`, `docs/<slug>`.
- One logical project change per PR. Do not mix RackTool, quota-bar, radar, and WF610 work.
- PR base is always `main`.
- Land with squash-merge and delete the head branch, unless the user asks for a different merge style.
- After merge, the feature branch should no longer exist on the remote.
- Do not reuse an old RackTool or Codex worktree to publish an unrelated project.

## Layout rules

- Every project lives under `projects/<project-slug>/`.
- Slugs are stable lowercase ASCII with hyphens: `wf610-ble`, not `WF610 BLE`.
- Keep each project self-contained: source, scripts, configs, README, changelog, privacy/security notes, and project assets stay inside that directory.
- Repository root only contains `README.md`, `AGENTS.md`, `.gitignore`, and `.github/`.
- Shared workflows live in `.github/workflows/` and must use `paths` filters so one project does not trigger another project's CI.
- When adding a maintained project, update the table in root `README.md` in the same PR.
- Do not nest a Git repository inside a project directory.

## Files that must not be committed

- `.venv/`, `.build/`, `dist/`, `.DS_Store`
- Built `.app` bundles, `.dmg`, `.zip`, `.tar.gz`
- Local installs such as `/Applications/WF610 BLE.app`
- SecureCRT session files, CRT logs, Bluetooth caches, Keychain material
- Private RackTool workbooks, customer names, or real rack Golden files
- Tokens, cookies, `auth.json`, and complete GATT or quota dumps

## Project-specific guidance

### `projects/codex-quota-bar/`

- Native macOS Objective-C menu bar utility.
- Run commands from inside `projects/codex-quota-bar/`.
- Validate:
  - `plutil -lint Info.plist`
  - `./build.sh`
  - `codesign --verify --deep --strict --verbose=2 "dist/Codex 额度栏.app"`
- Keep `.build/` and `dist/` untracked.

### `projects/deepseek-harness-radar/`

- Observation-only documentation project.
- `RADAR.md` is the current baseline; `history/YYYY-MM.md` stores monthly deltas.
- Do not install, download, run, or connect third-party DSH plugins.
- Do not modify the user's local DSH environment.
- Change `RADAR.md` only when the judgment actually changes.

### `projects/racktool/`

- Active V0.5 code project. Read `projects/racktool/AGENTS.md` before any RackTool task.
- `projects/racktool/README.md` is the current entry point; `README_PHASE0.md` is historical.
- Automated gates live under `projects/racktool/docs/gates/`. Headless PASS does not replace Excel/WPS or GUI manual validation.
- Keep private business workbooks Git-ignored. Do not substitute screenshots or synthetic fixtures for real Golden evidence.
- Do not create a nested Git repository under RackTool.

### `projects/wf610-ble/`

- Native macOS Swift menu-bar app plus a Python BLE-to-PTY bridge.
- Runtime scripts stay in `projects/wf610-ble/scripts/`; menu-bar source stays in `Sources/`.
- Local daily driver is `/Applications/WF610 BLE.app`. The GitHub copy is source, not the live app bundle.
- Do not commit `.venv/`, `dist/`, or `/Applications/WF610 BLE.app`.
- Do not open Classic SPP (`/dev/cu.WF610A`) and the BLE bridge at the same time.
- Validate:
  - `plutil -lint Info.plist`
  - `./build.sh`
  - `codesign --verify --deep --strict --verbose=2 "dist/WF610 BLE.app"`
- Live BLE/SecureCRT behavior can only be proven on this Mac; a green build does not prove the dongle is connected.

## Adding a new project

1. `mkdir -p projects/<slug>`
2. Put all project files in that directory.
3. Add `projects/<slug>/README.md` covering purpose, requirements, run/build, and current status.
4. Update the project table in root `README.md`.
5. If CI is needed, add `.github/workflows/<slug>.yml` with path filters limited to that project.
6. Ship it through a PR into `main`.

A documentation-only Phase 0 package may temporarily use `README_PHASE0.md` only when that project's accepted contract explicitly defers the final README.

## Language and commit messages

- Root `README.md` is the human homepage. Keep it short and in Chinese.
- This file stays in English so agents parse it consistently.
- Commit titles follow `feat(<slug>):`, `fix(<slug>):`, or `docs(<slug>):` for project work, and `docs:` / `chore:` for repository-wide files.
- Do not mention PRs of other projects in a commit that does not touch those projects.

## Forbidden shortcuts

- Do not edit files on `codex/racktool-*` or other unrelated branches to publish a different project.
- Do not squash-merge the wrong PR.
- Do not force-push `main`.
- Do not delete another project's files to make a tree look clean.
- Do not ask the user to click through routine GitHub steps that this contract already authorizes.
- If GitHub authentication or merge permission is actually missing, stop and say so; do not invent a local-only substitute and call the repository updated.
