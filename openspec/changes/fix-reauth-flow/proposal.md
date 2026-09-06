## Why

Re-authentication is broken. When the coordinator raises `ConfigEntryAuthFailed`, Home Assistant starts a reauth flow; the user re-enters credentials and a fresh verification token, authentication against the PerfectDraft API succeeds — and then the flow aborts with `already_configured`. The freshly minted tokens are thrown away, the config entry keeps its expired tokens, and HA immediately re-raises the "please re-authenticate" repair. The integration is unrecoverable through the UI: the only way back is to delete and re-add the entry, losing entity history and the restored keg-freshness baseline.

Root cause: `async_step_reauth_confirm` delegates to `async_step_token`, which is written exclusively for the initial-setup path. It unconditionally calls `async_set_unique_id(email)` followed by `_abort_if_unique_id_configured()` and then `async_create_entry()`. During reauth the unique ID *is* already configured — by the very entry being repaired — so the duplicate guard fires by design and the flow dies before it can persist anything.

## What Changes

- `async_step_token` becomes reauth-aware: on a successful authentication it either creates a new entry (initial setup, unchanged behaviour) or updates the existing entry and reloads it (reauth).
- On the reauth path, the duplicate-prevention guard `_abort_if_unique_id_configured()` is replaced by an identity guard that verifies the re-entered email still resolves to the entry under repair, so signing in with a *different* account during reauth is rejected rather than silently rebinding the entry.
- Successful reauth writes the new access, ID, and refresh tokens into the existing entry's data, preserves the already-discovered machine ID, reloads the entry, and aborts with `reauth_successful`.
- Reauth no longer re-derives the machine ID unnecessarily; the profile lookup is only needed when the entry has no machine ID recorded.
- One new abort string (`reauth_account_mismatch`) is added to `strings.json` and `translations/en.json` to explain the account-mismatch rejection. `reauth_successful` and `already_configured` already exist.
- Regression tests cover the reauth path so the `already_configured` abort cannot silently return.

## Capabilities

### New Capabilities

None. This change fixes behaviour already specified.

### Modified Capabilities

- `config-flow`: the existing "Reauth flow" requirement asserts that "on success, the config entry SHALL be updated with new tokens" — behaviour the implementation never had. The requirement is tightened into testable scenarios covering token persistence, entry reload, account-mismatch rejection, and the explicit prohibition on aborting with `already_configured` during reauth. The "Unique ID prevents duplicates" requirement is scoped to the user-initiated setup path so it no longer reads as applying to reauth.

## Impact

- `custom_components/perfectdraft/config_flow.py` — `async_step_token`, `async_step_reauth`, `async_step_reauth_confirm`.
- `custom_components/perfectdraft/strings.json` and `translations/en.json` — one new abort string.
- `hacs.json` — the fix uses config-flow helpers (`_get_reauth_entry`, `_abort_if_unique_id_mismatch`, `async_update_reload_and_abort` with `data_updates`) introduced in Home Assistant Core 2024.11, so a minimum core version is declared rather than left implicit.
- `tests/` — new test module for the config flow. Existing tests are stdlib-only (`test_keg_detection.py` imports the HA-free `keg_detection` module); config-flow tests need Home Assistant plus `pytest-homeassistant-custom-component`, so the test approach is a design decision, not a given.
- No API client, coordinator, or entity changes. No config entry version bump: the data schema is unchanged, only its contents are refreshed.
- Out of scope, noted while investigating: `PerfectDraftApiClient.refresh_access_token()` updates tokens in memory only and never writes them back to the config entry, so every HA restart burns one wasted 401-plus-refresh round trip. Harmless today because the Cognito refresh token is what actually gates reauth, and it is unchanged by a refresh. Tracked separately rather than bundled here.
