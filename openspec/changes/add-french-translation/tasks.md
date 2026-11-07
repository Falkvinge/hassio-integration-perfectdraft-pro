## 1. Worktree and contribution

- [ ] 1.1 `scripts/agent-worktree.sh create add-french-translation`; verify `.worktree/add-french-translation/.agent-lock` exists and `git worktree list` shows branch `agent/add-french-translation` at `master`
- [ ] 1.2 `git fetch github pull/14/head`, then in the worktree `git merge --ff-only 704f55e5958717899fea2265f1a3c627dd4cde9d`; verify `git log -1 --format='%H %an'` shows `704f55e…` by aurel and `git diff master --stat` lists only `translations/fr.json` and `tests/test_translations.py`
- [ ] 1.3 Verify the contribution against the spec: `fr.json` key set equals `strings.json`, and every string uses the same `{placeholder}` names as `strings.json`; then `../../.venv-test/bin/pytest tests/` from the worktree passes, including `test_translations.py`

## 2. Version

- [ ] 2.1 Bump `custom_components/perfectdraft/manifest.json` to 0.4.6 and commit as the maintainer; verify `git diff HEAD~1` is the single version line and the full suite still passes. Record the commit hash here

## 3. Project hygiene

- [ ] 3.1 Add a line to `PROJECT_HYGIENE.md` section 11 (main checkout): every new, renamed or removed key in `strings.json` must be mirrored in `translations/en.json` and `translations/fr.json` in the same commit, with a French string written rather than an English placeholder or a relaxed test; `tests/test_translations.py` enforces it. Commit in the main checkout; verify with `git log -1 -- PROJECT_HYGIENE.md`

## Workflow follow-up

- Archive per `AGENTS.md`: merge `agent/add-french-translation` into `master` with `--no-ff` (keeps `704f55e` intact), push `master` to `origin` and `github`, sync the `hacs-packaging` delta into `openspec/specs/`, archive, remove the worktree and branch.
- After the push, confirm via the GitHub API that PR #14 reports `merged: true`. If it doesn't, close it with a comment linking the merge commit.
- Tag `v0.4.6` and publish the GitHub release "v0.4.6 — French translation" in the format of v0.4.5: French UI for setup, errors and entity names; thanks to @Aurel004 for [#14](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/pull/14); note that the card stays at 0.4.5, no breaking changes, no re-configuration.
- Comment on PR #14 with a thank-you and the release link.
