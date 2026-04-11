# Agent Isolation Workflow

This repository uses per-agent worktree isolation. Every agent task must run in its own branch and worktree.

## Rules

- Do not edit from the shared integration checkout.
- Do not `git checkout` branches in shared checkouts while other agents may be active.
- Use one worktree per task and one branch per worktree.
- Keep a `.agent-lock` file in each active worktree.
- Keep OpenSpec change artifacts in the main checkout under `openspec/changes/`, even when implementation work happens in an agent worktree.

## Standard Flow

1. Create isolated worktree and branch from integration base:
   - `scripts/agent-worktree.sh create <topic> [base-branch]`
2. Work only in that worktree path:
   - `.worktree/<topic>`
   - Exception: create and edit OpenSpec documents in the main checkout at `openspec/changes/<topic>/`.
3. Commit and push branch:
   - `agent/<topic>`
4. Open PR into integration branch.
5. After merge, remove worktree:
   - `scripts/agent-worktree.sh remove <topic>`

## OpenSpec Artifact Persistence

Untracked files in the main checkout can vanish between agent sessions. To prevent loss of OpenSpec artifacts across phases (propose, apply, verify, archive):

1. **Commit after every phase.** After creating or updating artifacts under `openspec/changes/<topic>/`, immediately stage and commit them in the main checkout:
   ```bash
   git add openspec/changes/<topic>/
   git commit -m "openspec(<topic>): <phase> artifacts"
   ```
2. **Before any phase, verify artifacts exist.** At the start of apply, verify, or archive, confirm the change directory and its files are present. If missing, check `git log --all --oneline -- openspec/changes/<topic>/` to find and restore them before proceeding.
3. **Never re-scaffold over existing artifacts.** `openspec new change` refuses to overwrite, but if the directory was lost and you recreate it, the fresh `.openspec.yaml` resets artifact tracking. Restore from git history instead of re-creating.

**Branch boundary note:** Committing OpenSpec artifacts on the main checkout's branch while implementation lives on a worktree branch (e.g. `agent/<topic>`) is a deliberate cross-branch arrangement, not a mistake. It is safe because the `openspec/changes/<topic>/` namespace is exclusively owned by that change — no other branch or worktree writes to it. The OpenSpec skills resolve artifacts by absolute path in the main checkout, never via the worktree, so the branch separation is invisible to them.

## Archive = Full Close-Out

When archiving a change (`openspec-archive`), always perform the complete close-out sequence — not just the artifact move. The full sequence is:

1. **Commit** any uncommitted implementation work in the agent worktree.
2. **Merge** the agent branch into the integration branch from the main checkout.
3. **Push** the integration branch to origin.
4. **Archive** the change artifacts (`mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>`).
5. **Remove the worktree and branch:**
   ```bash
   git worktree remove .worktree/<topic> --force
   git branch -d agent/<topic>
   ```

"Done" means done — no orphan worktrees, no unmerged branches, no unpushed commits.

## Tech Stack

- Python 3.12+
- Home Assistant custom component (HACS-installable)
- `aiohttp` for async HTTP (HA's standard HTTP client)

## Lock File Contract

Each active worktree contains `.agent-lock` with owner/task/timestamp. If lock ownership is unclear, stop and ask before making edits.
