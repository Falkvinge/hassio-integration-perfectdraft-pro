## MODIFIED Requirements

### Requirement: Unique ID prevents duplicates
The config flow SHALL set a unique ID based on the lowercased user email. On the user-initiated setup path the flow SHALL abort when that unique ID already belongs to a configured entry. This duplicate guard SHALL NOT be applied on the reauth path, where a matching unique ID is the expected condition rather than a conflict.

#### Scenario: Duplicate prevention on user setup
- **WHEN** a user attempts to add the integration with an email that is already configured
- **THEN** the config flow SHALL abort with reason `already_configured`

#### Scenario: Unique ID normalisation
- **WHEN** the unique ID is set from a submitted email
- **THEN** it SHALL be the lowercased email, so that the same account entered with different capitalisation resolves to the same unique ID

#### Scenario: Duplicate guard not applied during reauth
- **WHEN** the flow reaches the token step with source `reauth`
- **THEN** the flow SHALL NOT abort with reason `already_configured`

### Requirement: Reauth flow
The integration SHALL support Home Assistant's reauth mechanism when the refresh token expires. A successful reauth SHALL update the existing config entry in place, reload it, and abort with `reauth_successful`. It SHALL NOT create a second config entry, and it SHALL NOT abort with `already_configured`.

#### Scenario: Reauth triggered
- **WHEN** the coordinator raises `ConfigEntryAuthFailed` because token refresh has failed
- **THEN** Home Assistant SHALL start a reauth flow for the affected entry
- **THEN** the flow SHALL show the `reauth_confirm` form pre-filled with the stored email
- **THEN** submitting credentials SHALL advance to the token step

#### Scenario: Reauth succeeds and persists new tokens
- **WHEN** the user submits a valid verification token during reauth and authentication succeeds
- **THEN** the existing config entry's access token, ID token, and refresh token SHALL be replaced with the newly issued values
- **THEN** the entry's stored email and machine ID SHALL be preserved unchanged
- **THEN** the entry SHALL be reloaded
- **THEN** the flow SHALL abort with reason `reauth_successful`
- **THEN** no additional config entry SHALL be created

#### Scenario: Reauth does not abort as already configured
- **WHEN** reauth authentication succeeds for the same account as the entry under repair
- **THEN** the flow SHALL NOT abort with reason `already_configured`
- **THEN** the "authentication failed, please re-authenticate" condition SHALL clear once the reloaded entry polls successfully

#### Scenario: Reauth with a different account is rejected
- **WHEN** the user submits credentials during reauth for an email whose lowercased value differs from the entry's unique ID, and authentication succeeds
- **THEN** the flow SHALL abort with reason `reauth_account_mismatch`
- **THEN** the existing config entry's tokens SHALL be left unchanged

#### Scenario: Reauth accepts the same account in different letter case
- **WHEN** the user re-enters the entry's email with different capitalisation during reauth
- **THEN** the flow SHALL treat it as the same account and complete successfully

#### Scenario: Reauth authentication fails
- **WHEN** the verification token is expired or the credentials are wrong during reauth
- **THEN** the flow SHALL show the `invalid_auth` error on the token form and allow retry with a fresh token
- **THEN** the existing config entry's tokens SHALL be left unchanged

#### Scenario: Machine ID lookup is skipped when already known
- **WHEN** reauth authentication succeeds and the existing entry already records a machine ID
- **THEN** the flow SHALL NOT call the user profile endpoint
- **THEN** the entry SHALL retain its recorded machine ID

#### Scenario: Machine ID recovered when absent
- **WHEN** reauth authentication succeeds and the existing entry has no machine ID recorded
- **THEN** the flow SHALL fetch the user profile and store the discovered machine ID on the entry

## ADDED Requirements

### Requirement: Minimum Home Assistant core version is declared
The integration SHALL declare a minimum supported Home Assistant core version of 2024.11.0 in `hacs.json`, because the config flow depends on reauth helpers introduced in that release.

#### Scenario: Installation on an unsupported core
- **WHEN** a user attempts to install the integration through HACS on a core older than 2024.11.0
- **THEN** HACS SHALL refuse the installation and report the minimum version, rather than allowing an install that fails at runtime

### Requirement: All abort reasons are translated
Every abort reason the config flow can emit SHALL have a corresponding entry under `config.abort` in `strings.json` and `translations/en.json`, so no user ever sees an untranslated reason key. The set of reasons SHALL be derived from the flow's source rather than maintained by hand, so that a newly reachable abort cannot ship untranslated.

#### Scenario: Mismatch message is rendered
- **WHEN** the reauth flow aborts with reason `reauth_account_mismatch`
- **THEN** the dialog SHALL render a translated message explaining that the credentials belong to a different account than the one being re-authenticated

#### Scenario: Concurrent flow for the same account is rejected
- **WHEN** a reauth flow is pending for an entry and the user starts a user-initiated setup for the same email
- **THEN** the second flow SHALL abort with reason `already_in_progress`
- **THEN** that reason SHALL render a translated message telling the user to finish or cancel the pending flow

#### Scenario: Abort reasons are enumerated from the source
- **WHEN** the translation coverage check runs
- **THEN** it SHALL enumerate abort reasons by inspecting the calls `config_flow.py` makes to aborting flow helpers, including reasons those helpers raise by default
- **THEN** it SHALL fail if any enumerated reason is absent from either translation file
