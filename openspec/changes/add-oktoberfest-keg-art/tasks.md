## 1. Worktrees

- [ ] 1.1 `scripts/agent-worktree.sh create add-oktoberfest-keg-art` in the integration repo, and an equivalent `.worktree/add-oktoberfest-keg-art` on branch `agent/add-oktoberfest-keg-art` in `Hassio-PerfectDraftPro-Component`; verify `.agent-lock` exists in both and `git worktree list` shows both branches

## 2. Integration rename

- [ ] 2.1 Change `"29745"` in `custom_components/perfectdraft/keg_catalog.json` to `"Löwenbräu Oktoberfestbier"`, in place; verify `git diff` is a single-line change and the file is still UTF-8 (written as literal characters, like `454`, not `\u` escapes)
- [ ] 2.2 Assert `catalog["29745"] == "Löwenbräu Oktoberfestbier"` in `tests/test_keg_catalog.py`, leaving `MINIMUM_ENTRIES` at 117; verify `python3 -m unittest tests.test_keg_catalog` passes
- [ ] 2.3 Bump `manifest.json` to 0.4.5 and commit; record the commit hash here for 3.3

## 3. Card artwork

Work in `Hassio-PerfectDraftPro-Component`.

- [ ] 3.1 Download the two source PNGs listed in design.md (no resize query string) to a scratch directory outside the repo; verify 1200×1200 and 700×700
- [ ] 3.2 Encode them with Pillow to `src/assets/kegs/lowenbrau-oktoberfest.webp` (800 px) and `src/assets/kegs/spaten-oktoberfest.webp` (700 px, not upscaled); verify the dimensions, a file size in the range of the existing art (about 25–40 KB), and a visual check of both files
- [ ] 3.3 Add `imagePath: kegImage("lowenbrau-oktoberfest")` and `imagePath: kegImage("spaten-oktoberfest")` to the two existing entries, changing no other field; re-sync `scripts/keg-catalog.reference.json` from the commit in 2.3 and set `_upstreamCommit` to it; verify the snapshot diff is only the `29745` name and the commit hash
- [ ] 3.4 Bump `package.json`, `CARD_VERSION` and `EDITOR_VERSION` to 0.4.5; regenerate `package-lock.json` with `npm install --package-lock-only`
- [ ] 3.5 `npm run lint`, `npm run check:catalog` (117/117, snapshot at the 2.3 commit) and `npm run build`; verify both `.webp` files are in `dist/kegs/`, then commit source and `dist/`

## 4. Joint verification

- [ ] 4.1 Install integration 0.4.5 and card 0.4.5 on Home Assistant; confirm the card editor's beer picker shows artwork for both Oktoberfest entries and that each renders sharply in the `hero` layout; with a 29745 or 33918 keg unavailable, also confirm `getBeerByKegId("29745")` and `getBeerByKegId("33918")` return entries with an `imagePath` in a browser console on the dashboard

## Workflow follow-up

- Joint release: integration v0.4.5 and card v0.4.5, published together. The release notes thank reimargithub, mention the 29745 rename for anyone matching the old string, and tell users to update both.
- After the release, close issue #8 with a thank-you and the release links.
- Archive per `AGENTS.md` in both repos (merge, push, archive, remove worktrees and branches). The change has no spec deltas to sync.
