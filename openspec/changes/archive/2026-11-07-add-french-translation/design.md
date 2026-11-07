## Context

PR #14 is one commit, `704f55e` by aurel <aurelien.ruat@hotmail.fr>, whose parent is the current `master` head (`851ec3a`). GitHub reports it mergeable with no conflicts. Checked before this change:

- `fr.json` has exactly the key set of `strings.json` and `en.json`, which also match each other.
- Every `{reason}` placeholder and the README link in the token step are carried over.
- The full suite passes on the PR branch: 77 tests, 587 subtests, including the new `test_translations.py`.

`git fetch github pull/14/head` makes the commit available locally.

## Goals / Non-Goals

**Goals:**
- Ship the contribution byte-for-byte, with aurel as the commit author, and have GitHub show PR #14 as merged.

**Non-Goals:**
- Editing the French wording or the contributed test (style, unittest vs pytest, hardcoded `("en", "fr")`).

## Decisions

**Merge the original commit, not a squash or a re-applied diff.** The worktree branch `agent/add-french-translation` starts at `master` and fast-forwards to `704f55e`; the version bump is a separate maintainer commit on top. When the branch is later merged into `master` and pushed to `github`, `704f55e` is reachable from the PR's base branch, so GitHub marks PR #14 merged and attributes the commit to aurel. Squashing or cherry-picking would change the hash, lose that link, and need a manual PR close.

**Integration-only patch release (0.4.6).** The card has no translation files, so it is unchanged. The versioning rule in `PROJECT_HYGIENE.md` allows a diverging patch.

**Keep the test strict.** Home Assistant falls back to English for missing keys, so partial translations would work at runtime. The maintainer chose exact parity instead, so French never falls silently behind. The cost is one more file to touch per string change, recorded in `PROJECT_HYGIENE.md`.

## Risks / Trade-offs

- [A future agent adds a string to `strings.json` and `en.json` only] → The test fails in that change; the `PROJECT_HYGIENE.md` note tells the agent to write the French entry rather than relax the test.
- [The new strings are shown on a narrow UI and truncate] → Not seen in testing, and the contributor runs it live. Fix in a follow-up only if a user reports it.
- [No on-device check on the dev host] → As with 0.4.4 and 0.4.5, there is no Home Assistant on the dev host. The contributor's own instance is the live check; the static checks above cover the files.

## Migration Plan

None. Updating via HACS and restarting Home Assistant picks up `fr.json`. Rollback is reinstalling 0.4.5.
