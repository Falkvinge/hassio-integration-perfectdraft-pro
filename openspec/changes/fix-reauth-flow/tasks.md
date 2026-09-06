## 1. Isolate the work

- [x] 1.1 Create the agent worktree and branch: `scripts/agent-worktree.sh create fix-reauth-flow master`
- [x] 1.2 Confirm `.agent-lock` exists in `.worktree/fix-reauth-flow` and records this task
- [x] 1.3 Confirm the worktree base includes merge commit `3b69942` (PR #2 mirrored to both remotes)

## 2. Test harness

- [x] 2.1 Add `requirements-test.txt` pinning `pytest-homeassistant-custom-component==0.13.205` (newest release still supporting Python 3.12; pins core 2025.1.4, above the 2024.11 floor). Also pins `pycares==4.5.0` — core pins `aiodns==3.2.0` but leaves pycares floating, and pycares 4.6+ starts a daemon shutdown thread that the harness's `verify_cleanup` fixture flags as a leak, erroring every test at teardown.
- [x] 2.2 Add `tests/conftest.py` enabling custom integrations (the `auto_enable_custom_integrations` fixture) so `custom_components/perfectdraft` is loadable by the `hass` fixture
- [x] 2.3 Add `pytest.ini` with `asyncio_mode = auto` and `pythonpath = .` so `custom_components` is importable; confirm `pytest tests/` collects
- [x] 2.4 Confirm `python3 -m unittest discover -s tests` still passes standalone. Required guarding the Home Assistant imports in `test_config_flow.py` with a `unittest.SkipTest` raised on `ImportError` — unittest converts that into a skip rather than a collection error. Result: 11 passed, 1 skipped.

## 3. Failing regression tests

Write these against the current broken code first and watch them fail for the right reason — an `already_configured` abort, not an import or fixture error.

- [x] 3.1 `tests/test_config_flow.py`: reauth with a valid token updates the existing entry's access, ID, and refresh tokens
- [x] 3.2 Same test asserts the entry's email and machine ID are unchanged and that `hass.config_entries.async_entries(DOMAIN)` still has length 1
- [x] 3.3 Assert the reauth flow's result type is `ABORT` with reason `reauth_successful`, and explicitly assert the reason is not `already_configured`
- [x] 3.4 Reauth with a different account's email aborts with `reauth_account_mismatch` and leaves the stored tokens untouched
- [x] 3.5 Reauth re-entering the same email in different capitalisation succeeds
- [x] 3.6 Reauth with a rejected token shows the `invalid_auth` error on the token form and leaves the stored tokens untouched
- [x] 3.7 Reauth does not call the user profile endpoint when the entry already records a machine ID
- [x] 3.8 Reauth fetches the profile and stores the machine ID when the entry has none
- [x] 3.9 Initial user setup still creates an entry, and a second setup with an already-configured email still aborts with `already_configured`

Confirmed failing against unfixed code: 8 failed, 7 passed. The headline assertion failed as `assert 'already_configured' != 'already_configured'` — the reported bug, reproduced exactly.

## 4. Implement the fix

- [x] 4.1 Reference `SOURCE_REAUTH` as `config_entries.SOURCE_REAUTH` rather than adding a bare import — the module already qualifies every other `config_entries` symbol, so this matches existing style and adds no import line
- [x] 4.2 In `async_step_token`, replace the unconditional `_abort_if_unique_id_configured()` + `async_create_entry()` terminal block with the source-aware branch from design Decision 1
- [x] 4.3 On the reauth branch, call `_abort_if_unique_id_mismatch(reason="reauth_account_mismatch")` then `async_update_reload_and_abort(reauth_entry, data_updates={...})`. Extracted into `_async_persist()` because both the machine-ID-known and machine-ID-recovered paths terminate through it.
- [x] 4.4 Make the machine ID lookup conditional: skip `get_user_profile()` when the source is reauth and the entry already has `CONF_MACHINE_ID`; otherwise fetch as today and include it in the data written
- [x] 4.5 Confirm the non-reauth branch is behaviourally identical to today's setup path (guarded by tasks 3.9 and the connection-error test)

## 5. Strings and packaging

- [x] 5.1 Add `reauth_account_mismatch` under `config.abort` in `custom_components/perfectdraft/strings.json`
- [x] 5.2 Mirror the same key and message into `custom_components/perfectdraft/translations/en.json`
- [x] 5.3 Cross-check that every abort reason reachable from `config_flow.py` (`already_configured`, `reauth_successful`, `reauth_account_mismatch`) is present in both files — enforced by a parametrised test, not just inspection
- [x] 5.4 Add `"homeassistant": "2024.11.0"` to `hacs.json`
- [x] 5.5 Set `version` in `manifest.json` to `0.3.1`. Note the merged PR #2 had bumped it to `0.4.0`; no `v0.4.0` tag exists on either remote, so nothing was ever released under that number and stepping down to `0.3.1` breaks no HACS update path.
- [x] 5.6 Verify `strings.json`, `translations/en.json`, `hacs.json`, and `manifest.json` all still parse as JSON
- [x] 5.7 Add `.venv-test/` and `.pytest_cache/` to `.gitignore`

## 6. Verify

- [x] 6.1 All tests from section 3 pass: 26 passed (15 config flow + 11 keg detection)
- [x] 6.2 `python3 -m unittest discover -s tests` still passes: 11 passed, 1 skipped
- [x] 6.3 `python3 -m compileall -q custom_components/perfectdraft/` is clean
- [ ] 6.4 On-device: install the branch on the live HA instance, forge an expired session by editing `access_token`/`refresh_token` in `config/.storage/core.config_entries`, restart, and confirm the reauth repair appears
- [ ] 6.5 On-device: complete the reauth flow with a fresh verification token and confirm it ends on "Re-authentication successful" — not "already configured"
- [ ] 6.6 On-device: confirm the integration polls successfully afterwards, entity history is continuous, and the keg-freshness baseline survived (no reset to unknown)
- [ ] 6.7 On-device: confirm entering a different account's email during reauth is rejected with the mismatch message

## 7. Close out

- [x] 7.1 Commit on `agent/fix-reauth-flow` with a message explaining why `_abort_if_unique_id_configured` was the wrong helper for the reauth source
- [x] 7.2 Merge into `master` from the main checkout
- [x] 7.3 Push `master` to `origin` (git.falkvinge.net) and to `github` so both remotes stay at parity
- [x] 7.4 Sync the delta spec into `openspec/specs/config-flow/spec.md` to reflect what was actually built
- [ ] 7.5 Archive: `mv openspec/changes/fix-reauth-flow openspec/changes/archive/<YYYY-MM-DD>-fix-reauth-flow` — held until on-device verification (6.4–6.7) confirms the fix on the live machine
- [ ] 7.6 Remove the worktree and branch: `git worktree remove .worktree/fix-reauth-flow --force && git branch -d agent/fix-reauth-flow` — held with 7.5
- [x] 7.7 Record the deferred item (persisting Cognito-refreshed tokens back to the config entry) as a TODO in `PROJECT_HYGIENE.md` section 11
