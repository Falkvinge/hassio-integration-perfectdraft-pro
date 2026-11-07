## 1. Name and worktrees

- [ ] 1.1 Ask MThomas564 on PR #10 whether the keg or the PerfectDraft app calls 48180 "Camden Stout" or "Camden Nitro Stout"; record the answer (or "no reply by release, shipping Camden Stout") in this file
  - Asked 2026-11-07: https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/pull/10#issuecomment-6706008826 — awaiting reply; implementation proceeds with "Camden Stout"
- [x] 1.2 `scripts/agent-worktree.sh create add-keg-48180` in the integration repo, and an equivalent `.worktree/add-keg-48180` on branch `agent/add-keg-48180` in `Hassio-PerfectDraftPro-Component`; confirm `.agent-lock` in both

## 2. Integration catalog

- [x] 2.1 Add `"48180": "<name from 1.1>"` to `keg_catalog.json` as the last key, after `48134`
- [x] 2.2 Ratchet `MINIMUM_ENTRIES` to 117 in `tests/test_keg_catalog.py` and assert `catalog["48180"]`; verify `python3 -m unittest tests.test_keg_catalog` passes (117 keys, ascending order)
- [x] 2.3 Change the README catalog count from 116 to 117 in place, touching no other table cell or padding; verify `git diff README.md` is a single-line change
- [x] 2.4 Commit with `Co-authored-by: MThomas564` (address from his PR #10 commit); do not touch `manifest.json`

## 3. Companion card

Work in `Hassio-PerfectDraftPro-Component`.

- [x] 3.1 Take `src/assets/kegs/camden-stout.webp` from card PR #2's head commit unchanged
- [x] 3.2 Add the `camden-stout` entry (name from 1.1, Camden Town Brewery, Stout, PR #2 colours, `imagePath: kegImage("camden-stout")`, `kegId: "48180"`) next to the other Camden rows; check the ABV against Camden's or PerfectDraft's product page and use that value
  - ABV 4.0% confirmed on Camden Town Brewery's "Camden X PerfectDraft Stout" listing (camdentownbrewery.com, 2026-11-07), which also calls the keg "Camden Stout"
- [x] 3.3 Re-sync `scripts/keg-catalog.reference.json` from the integration commit in 2.4 and set `_upstreamCommit` to it
- [x] 3.4 Bump `package.json`, `CARD_VERSION` and `EDITOR_VERSION` to 0.4.3; regenerate `package-lock.json` with `npm install --package-lock-only` rather than copying PR #2's
- [x] 3.5 `npm run lint`, `npm run check:catalog` (117/117), `npm run build`; commit source and `dist/` with `Co-authored-by: MThomas564`

## 4. Joint verification

- [ ] 4.1 With `fix-cognito-signin` also applied, install integration 0.3.5 and card 0.4.3 on Home Assistant; if a 48180 keg is unavailable, confirm instead that the card editor's beer picker lists the new entry with its artwork, and that `getBeerByKegId("48180")` resolves it in a browser console on the dashboard

## Workflow follow-up

- Before archiving this change, archive `add-keg-47792` (complete since v0.3.4, never archived), so the `entities` main spec reads 116 before this delta lifts it to 117.
- Joint release: integration v0.3.5 (with `fix-cognito-signin`) and card v0.4.3, published together. The release notes thank MThomas564 and tell users to update both.
- After the release, close PR #10, card PR #2 and issue #9, each with a thank-you, the commit links and the release link.
- Archive per `AGENTS.md` in both repos (merge, push, sync the `entities` spec, archive, remove worktrees and branches).
