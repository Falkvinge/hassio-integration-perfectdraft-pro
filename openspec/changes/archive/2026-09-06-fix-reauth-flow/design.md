## Context

The config flow has three entry points that converge on one terminal step:

```
async_step_user ──────────────┐
                              ├──> async_step_token ──> async_create_entry
async_step_reauth ──> async_step_reauth_confirm ──┘
```

`async_step_token` is the only place that talks to the API and the only place that persists tokens. It was written for the initial-setup path and never made aware that reauth also lands there:

```100:111:custom_components/perfectdraft/config_flow.py
                    await self.async_set_unique_id(self._email.lower())
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"PerfectDraft ({self._email})",
                        data={
                            CONF_EMAIL: self._email,
                            CONF_ACCESS_TOKEN: client.access_token,
                            CONF_ID_TOKEN: client.id_token,
                            CONF_REFRESH_TOKEN: client.refresh_token,
                            CONF_MACHINE_ID: machine_id,
                        },
                    )
```

During reauth the unique ID resolves to the entry being repaired, so `_abort_if_unique_id_configured()` fires and the flow terminates with `already_configured` before reaching `async_create_entry`. This is the documented behaviour of that helper — it is simply the wrong helper for this source. The observed symptom chain follows directly: authentication succeeds (the "churning"), the abort surfaces "already configured", the entry retains its dead tokens, and the coordinator's next `ConfigEntryAuthFailed` re-raises the reauth repair.

Constraints on the fix:

- The reauth path must reach the *same* API calls as setup. PerfectDraft's `/authentication/sign-in` requires a fresh reCAPTCHA token with a two-minute lifetime, so reauth genuinely needs the full email/password/token sequence — there is no silent re-auth to fall back on. Sharing `async_step_token` between sources is correct; only its terminal branch is wrong.
- The entry must be preserved, not recreated. Recreating would change `entry_id`, orphan every entity's `unique_id`, and discard the keg-freshness baseline that `PerfectDraftKegFreshnessSensor` restores via `RestoreEntity`.
- `CONF_MACHINE_ID` already lives in the entry. Reauth should not depend on rediscovering it.

## Goals / Non-Goals

**Goals:**

- Reauth completes: fresh tokens land in the existing config entry, the entry reloads, the repair clears.
- Reauth can never abort with `already_configured`.
- Signing in as a different account during reauth is rejected with a clear message, not silently rebound onto the existing entry.
- The initial-setup path behaves exactly as it does today, including duplicate prevention.
- Automated regression coverage for all of the above.

**Non-Goals:**

- Persisting Cognito-refreshed access/ID tokens back to the config entry during normal polling. Noted in the proposal, tracked separately.
- Eliminating the reCAPTCHA token requirement from reauth. The upstream API mandates it.
- A `reconfigure` step. Nothing in the entry data is user-editable outside of credentials.
- Any change to token refresh, coordinator, or entity behaviour.

## Decisions

### Decision 1: Branch inside `async_step_token` on `self.source`, using HA's reauth helpers

The terminal branch becomes:

```python
await self.async_set_unique_id(self._email.lower())

if self.source == SOURCE_REAUTH:
    self._abort_if_unique_id_mismatch(reason="reauth_account_mismatch")
    return self.async_update_reload_and_abort(
        self._get_reauth_entry(),
        data_updates={
            CONF_ACCESS_TOKEN: client.access_token,
            CONF_ID_TOKEN: client.id_token,
            CONF_REFRESH_TOKEN: client.refresh_token,
        },
    )

self._abort_if_unique_id_configured()
return self.async_create_entry(...)
```

This is verbatim the pattern Home Assistant's developer documentation prescribes for flows whose steps are shared between `user` and `reauth` sources. `data_updates` merges into the existing entry data, so `CONF_EMAIL` and `CONF_MACHINE_ID` survive untouched. `async_update_reload_and_abort` reloads the entry and aborts with `reauth_successful` by default, which is exactly the desired terminal state and is already translated in `strings.json`.

*Alternative considered — a separate reauth-specific token step.* Duplicating the authenticate/profile/error-handling block into `async_step_reauth_token` would avoid the source check, but it clones roughly forty lines of error handling that must then stay in sync across two paths. The bug being fixed here is precisely a divergence between setup and reauth expectations; duplicating the code invites the next one.

*Alternative considered — hand-rolled entry update for pre-2024.11 compatibility.* `self.hass.config_entries.async_get_entry(self.context["entry_id"])`, a manual unique-ID comparison, `async_update_entry`, `async_reload`, and `self.async_abort(reason="reauth_successful")` reproduce the helpers' behaviour on older cores. Rejected: it is more code, it is the pattern HA explicitly deprecated in favour of the helpers, and 2024.11 shipped in November 2024 — a floor that is nearly two years old.

### Decision 2: Declare `"homeassistant": "2024.11.0"` in `hacs.json`

`_get_reauth_entry`, `_abort_if_unique_id_mismatch`, and the `data_updates` parameter of `async_update_reload_and_abort` all landed in Home Assistant Core 2024.11. The repo currently declares no minimum core version anywhere, so on an older core the fix would fail with an `AttributeError` mid-flow — a worse failure than the bug it replaces. HACS reads the `homeassistant` key and blocks installation below that floor, turning a runtime crash into an install-time message.

Note this belongs in `hacs.json`, not `manifest.json`: integration manifests have no minimum-core-version field.

### Decision 3: Custom abort reason `reauth_account_mismatch` over the default

`_abort_if_unique_id_mismatch()` defaults to reason `unique_id_mismatch`. Either reason needs a corresponding entry under `config.abort` in `strings.json` and `translations/en.json`, since custom components cannot use core's `[%key:common::...]` translation references. Given a string must be written regardless, the specific reason carries the actionable message — the user re-entered a different account's email and needs to use the original one, or delete the entry and add the new account fresh.

### Decision 4: Test with `pytest-homeassistant-custom-component`

Config-flow behaviour cannot be verified without instantiating Home Assistant: the failure is in `ConfigFlow` helper interaction, not in any extractable pure function. `pytest-homeassistant-custom-component` is the standard harness for custom integrations and provides `hass`, `MockConfigEntry`, and the flow-driving helpers needed to assert on abort reasons and post-flow entry data.

This adds the repo's first dev dependency. It goes in a new `requirements-test.txt` so the runtime component stays dependency-free (`manifest.json` keeps `"requirements": []`), and the existing stdlib-only `test_keg_detection.py` continues to run under plain `python3 -m unittest` for anyone who does not install the harness.

The harness version must be pinned to match a core version at or above the 2024.11 floor; `pytest-homeassistant-custom-component` releases track core releases one-to-one.

*Alternative considered — stubbing HA modules with `unittest.mock`.* Cheap, no dependency, and worthless here: the bug lives in the real behaviour of `_abort_if_unique_id_configured` against a real config entry registry. A stub would encode our assumption about that helper rather than test it, and would have passed against the broken code.

### Decision 5: Keep the profile lookup conditional on a missing machine ID

Reauth currently re-fetches `/api/me` to extract the machine ID, then discards it in the abort. Since `data_updates` preserves the stored `CONF_MACHINE_ID`, the call is redundant on the reauth path whenever the entry already has one. Skipping it removes a network round trip from a flow the user is actively waiting on, and removes a failure mode where a transient `/api/me` error turns a successful authentication into `cannot_connect`. The lookup is retained when the entry has no machine ID recorded, which keeps the reauth path capable of healing an entry that was created before a machine was registered.

## Risks / Trade-offs

**The 2024.11 floor excludes users on older cores.** → Two years of core releases is a generous floor for an integration whose current release is 0.3.0, and HACS surfaces the requirement at install time rather than as a runtime crash. Users below it are already missing security fixes.

**`self.source` is unreliable if a step is reached by an unanticipated route.** → The flow has exactly three entry points, all enumerated above, and `SOURCE_REAUTH` is set by Home Assistant itself when it starts the repair. The `else` branch retains `_abort_if_unique_id_configured()`, so any unforeseen source keeps today's conservative duplicate-prevention behaviour rather than silently overwriting an entry.

**Email case sensitivity determines whether the mismatch guard fires correctly.** → `async_set_unique_id(self._email.lower())` already normalises, and the stored unique ID was written by the same expression at setup time. The reauth form pre-fills the stored email, so the common path compares identical strings. A test asserting that a differently-cased re-entry of the *same* address is accepted pins this down.

**Adding a test dependency risks breaking the existing lightweight test run.** → `requirements-test.txt` is opt-in and `test_keg_detection.py` keeps its stdlib-only imports, so `python3 -m unittest discover -s tests` continues to work standalone. Verification during implementation must confirm both runners pass.

## Migration Plan

No data migration. The config entry schema is unchanged — `VERSION` stays 1 and `async_migrate_entry` is untouched — because only the *values* of the token fields are refreshed.

Deployment is a normal integration update. Users currently stuck in the reauth loop recover by re-running reauth after updating; no delete-and-re-add is required, and entity history plus the keg-freshness baseline are preserved. Rollback is reverting the commit: it restores the bug but corrupts nothing, since entries written by the fixed code are schema-identical to entries written by the broken code.

## Open Questions

None blocking. The one deferred item — persisting Cognito-refreshed tokens back to the config entry — is recorded in the proposal's Impact section for a separate change.
