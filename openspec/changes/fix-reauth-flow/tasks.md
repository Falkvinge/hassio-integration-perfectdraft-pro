## 1. Isolate the work

- [ ] 1.1 Create the agent worktree and branch: `scripts/agent-worktree.sh create fix-reauth-flow master`
- [ ] 1.2 Confirm `.agent-lock` exists in `.worktree/fix-reauth-flow` and records this task
- [ ] 1.3 Confirm the worktree base includes merge commit `3b69942` (PR #2 mirrored to both remotes)

## 2. Test harness

- [ ] 2.1 Add `requirements-test.txt` pinning `pytest-homeassistant-custom-component` to a release tracking core 2024.11 or newer, plus `pytest-asyncio` if the pin does not supply it
- [ ] 2.2 Add `tests/conftest.py` enabling custom integrations (the `auto_enable_custom_integrations` fixture) so `custom_components/perfectdraft` is loadable by the `hass` fixture
- [ ] 2.3 Install the harness into `.venv` and confirm `pytest tests/` collects
- [ ] 2.4 Confirm `python3 -m unittest discover -s tests` still passes standalone, proving `test_keg_detection.py` kept its stdlib-only imports

## 3. Failing regression tests

Write these against the current broken code first and watch them fail for the right reason — an `already_configured` abort, not an import or fixture error.

- [ ] 3.1 `tests/test_config_flow.py`: reauth with a valid token updates the existing entry's access, ID, and refresh tokens
- [ ] 3.2 Same test asserts the entry's email and machine ID are unchanged and that `hass.config_entries.async_entries(DOMAIN)` still has length 1
- [ ] 3.3 Assert the reauth flow's result type is `ABORT` with reason `reauth_successful`, and explicitly assert the reason is not `already_configured`
- [ ] 3.4 Reauth with a different account's email aborts with `reauth_account_mismatch` and leaves the stored tokens untouched
- [ ] 3.5 Reauth re-entering the same email in different capitalisation succeeds
- [ ] 3.6 Reauth with a rejected token shows the `invalid_auth` error on the token form and leaves the stored tokens untouched
- [ ] 3.7 Reauth does not call the user profile endpoint when the entry already records a machine ID
- [ ] 3.8 Reauth fetches the profile and stores the machine ID when the entry has none
- [ ] 3.9 Initial user setup still creates an entry, and a second setup with an already-configured email still aborts with `already_configured`

## 4. Implement the fix

- [ ] 4.1 Import `SOURCE_REAUTH` from `homeassistant.config_entries` in `config_flow.py`
- [ ] 4.2 In `async_step_token`, replace the unconditional `_abort_if_unique_id_configured()` + `async_create_entry()` terminal block with the source-aware branch from design Decision 1
- [ ] 4.3 On the reauth branch, call `_abort_if_unique_id_mismatch(reason="reauth_account_mismatch")` then `async_update_reload_and_abort(self._get_reauth_entry(), data_updates={...})` carrying only the three token fields
- [ ] 4.4 Make the machine ID lookup conditional: skip `get_user_profile()` when the source is reauth and `self._get_reauth_entry().data` already has `CONF_MACHINE_ID`; otherwise fetch as today and include it in the data written
- [ ] 4.5 Confirm the non-reauth branch is byte-for-byte equivalent in behaviour to today's setup path

## 5. Strings and packaging

- [ ] 5.1 Add `reauth_account_mismatch` under `config.abort` in `custom_components/perfectdraft/strings.json` with a message naming the mismatch and the two ways out (use the original account, or delete the entry and add the new one)
- [ ] 5.2 Mirror the same key and message into `custom_components/perfectdraft/translations/en.json`
- [ ] 5.3 Cross-check that every abort reason reachable from `config_flow.py` (`already_configured`, `reauth_successful`, `reauth_account_mismatch`) is present in both files
- [ ] 5.4 Add `"homeassistant": "2024.11.0"` to `hacs.json`
- [ ] 5.5 Bump `version` in `manifest.json` to `0.3.1`
- [ ] 5.6 Verify `strings.json`, `translations/en.json`, `hacs.json`, and `manifest.json` all still parse as JSON

## 6. Verify

- [ ] 6.1 All tests from section 3 pass: `pytest tests/ -v`
- [ ] 6.2 `python3 -m unittest discover -s tests` still passes (11 keg-detection tests)
- [ ] 6.3 `python3 -m compileall -q custom_components/perfectdraft/` is clean
- [ ] 6.4 On-device: install the branch on the live HA instance, forge an expired session by editing `access_token`/`refresh_token` in `config/.storage/core.config_entries`, restart, and confirm the reauth repair appears
- [ ] 6.5 On-device: complete the reauth flow with a fresh verification token and confirm it ends on "Re-authentication successful" — not "already configured"
- [ ] 6.6 On-device: confirm the integration polls successfully afterwards, entity history is continuous, and the keg-freshness baseline survived (no reset to unknown)
- [ ] 6.7 On-device: confirm entering a different account's email during reauth is rejected with the mismatch message

## 7. Close out

- [ ] 7.1 Commit on `agent/fix-reauth-flow` with a message explaining why `_abort_if_unique_id_configured` was the wrong helper for the reauth source
- [ ] 7.2 Merge into `master` from the main checkout
- [ ] 7.3 Push `master` to `origin` (git.falkvinge.net) and to `github` so both remotes stay at parity
- [ ] 7.4 Sync the delta spec into `openspec/specs/config-flow/spec.md` to reflect what was actually built
- [ ] 7.5 Archive: `mv openspec/changes/fix-reauth-flow openspec/changes/archive/<YYYY-MM-DD>-fix-reauth-flow`
- [ ] 7.6 Remove the worktree and branch: `git worktree remove .worktree/fix-reauth-flow --force && git branch -d agent/fix-reauth-flow`
- [ ] 7.7 Record the deferred item (persisting Cognito-refreshed tokens back to the config entry) as a TODO in `PROJECT_HYGIENE.md` section 11, alongside the existing pour-count TODO
