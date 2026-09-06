## 1. Set up the worktree

- [x] 1.1 Create the isolated worktree and branch: `scripts/agent-worktree.sh create backport-keg-catalog`
- [x] 1.2 Write `.agent-lock` in `.worktree/backport-keg-catalog` with owner, task, and timestamp
- [x] 1.3 Confirm the fork's catalog is available to copy from — clone `https://github.com/brettjenkins/hassio-integration-perfectdraft-pro.git` to a scratch dir if `/tmp/bj-fork` is gone, and verify `git show origin/master:custom_components/perfectdraft/keg_catalog.json` parses as JSON with 114 entries

## 2. Backport the catalog data

- [x] 2.1 Record the pre-change baseline: entry count (expect 86) and the current names for IDs 32814, 43235, 44331, 44536
- [x] 2.2 Copy the fork's `custom_components/perfectdraft/keg_catalog.json` over the worktree's copy
- [x] 2.3 Diff against `master` and confirm the change is exactly 28 added IDs, 4 changed names, and one added trailing newline — no reordering, no reindentation, no other name edits
- [x] 2.4 Confirm the 4 changed names are only the intended ones: 32814 → "Romola", 43235 → "Corona Cero (0.0% abv)", 44331 → "Ninkasi Flower Lager", 44536 → "Tiny Rebel Stay Puft"
- [x] 2.5 Confirm none of the 11 styling-only differences were pulled in (spot-check Trooper and St Feuillien)

## 3. Verify the file mechanically

- [x] 3.1 Assert `json.load` succeeds and `len()` is exactly 114 — a duplicate key would silently collapse and change the count
- [x] 3.2 Assert every key parses as an int and every value is a non-empty string
- [x] 3.3 Assert keys are in ascending numeric order
- [x] 3.4 Assert no value contains shop-listing artefacts: `6L`, `Short Date`, or `BBE`
- [x] 3.5 Assert all 86 original IDs are still present (superset check)
- [x] 3.6 Import `sensor.py`'s loader against the new file and confirm `_KEG_CATALOG` has 114 int-keyed entries

## 4. Bump the version

- [x] 4.1 Set `custom_components/perfectdraft/manifest.json` version to `0.3.2` — continuing from 0.3.1, not from the fork's 0.4.1
- [x] 4.2 Leave `hacs.json` untouched, including the `homeassistant: 2024.11.0` floor

## 5. Verify on the machine

**DEFERRED to post-release on-device check — carried as verification debt.**
The v0.3.2 release exists so the owner can install via HACS and run this group live.

**Why it could not be done here.** No Home Assistant instance is reachable from the
dev host (nothing on `localhost:8123`), and the standalone route failed too: the
refresh token in `.credentials.json` is expired, so `refresh_access_token()` returns
`NotAuthorizedException: Refresh Token has expired`. Recovering it needs the browser
reCAPTCHA step from the README, which only the owner can do.

Note also that `test_harness.py` expects a `user_id` key that `.credentials.json` no
longer has — pre-existing drift, unrelated to this change, left alone.

Static verification stands in for now and is recorded in groups 2 and 3: the diff shape
is confirmed exactly (28 added, 0 removed, 4 changed), the loader transform was
reproduced to 114 int keys, and `tests/test_keg_catalog.py` guards the format
permanently. What remains unproven is only that the live integration still resolves the
fitted keg after the file was replaced wholesale.

- [ ] 5.1 Deploy to Home Assistant and reload the integration
- [ ] 5.2 Confirm the `Keg` sensor still resolves the currently fitted keg's name correctly (regression check — the file was replaced wholesale)
- [ ] 5.3 Confirm the `Keg Product` sensor reports the same product ID as before the change
- [ ] 5.4 Confirm no new errors in the HA log from `custom_components.perfectdraft`
- [ ] 5.5 If the currently fitted keg is one of the 4 corrected IDs, record the before/after name for the release notes

## 6. Sync specs and close out

- [x] 6.1 Run `openspec validate --changes backport-keg-catalog` and fix any reported issues
- [x] 6.2 Commit in the worktree with a message explaining the provenance of the data and naming the 4 corrections
- [x] 6.3 Mark tasks complete and commit the artifact updates in the main checkout
- [x] 6.4 Sync the `entities` delta into `openspec/specs/entities/spec.md`
- [x] 6.5 Merge `agent/backport-keg-catalog` into `master`, push, and archive the change
- [x] 6.6 Remove the worktree and branch: `git worktree remove .worktree/backport-keg-catalog --force && git branch -d agent/backport-keg-catalog`
