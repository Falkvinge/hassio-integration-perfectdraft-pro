## MODIFIED Requirements

### Requirement: Token step collects verification token
The config flow SHALL present a form requesting a reCAPTCHA verification token as the second step, with instructions linking to the README. When authentication fails, the flow SHALL tell the user which input was rejected and show the server's reason.

#### Scenario: Token step display
- **WHEN** the user reaches the token step
- **THEN** the description SHALL render without translation errors (no curly braces or newlines)
- **THEN** the description SHALL contain a clickable link to the setup instructions on GitHub
- **THEN** the description SHALL mention the 2-minute token expiry

#### Scenario: Valid token submitted
- **WHEN** the user submits a valid token
- **THEN** the flow SHALL call `authenticate()` with the email, password, and token
- **THEN** on success, it SHALL fetch the user profile to discover the machine ID
- **THEN** it SHALL create a config entry storing email, access token, ID token, refresh token, and machine ID

#### Scenario: Invalid or expired token
- **WHEN** authentication fails as a verification token failure
- **THEN** the flow SHALL show the token form again with the `token_rejected` error, including the server's reason
- **THEN** the user SHALL be able to retry with a fresh token

#### Scenario: Wrong email or password
- **WHEN** authentication fails as a credentials failure
- **THEN** the flow SHALL show the credentials form again with the `invalid_credentials` error, including the server's reason
- **THEN** that form SHALL be the email and password form during setup, and the `reauth_confirm` form during reauth
- **THEN** after the user resubmits credentials, the flow SHALL ask for a fresh token

#### Scenario: Other authentication failure
- **WHEN** authentication fails for any other reason
- **THEN** the flow SHALL show the token form again with the `invalid_auth` error, including the server's reason
- **THEN** the user SHALL be able to retry with a fresh token

#### Scenario: Failure without a server reason
- **WHEN** authentication fails and the server supplied no reason
- **THEN** the error message SHALL still render, with a fixed fallback in place of the reason and no unfilled placeholder

#### Scenario: API unreachable
- **WHEN** the API is unreachable
- **THEN** the flow SHALL show a connection error

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
- **WHEN** the verification token or the credentials are rejected during reauth
- **THEN** the flow SHALL show the same error, on the same form, as the matching failure during setup (`token_rejected`, `invalid_credentials` on the `reauth_confirm` form, or `invalid_auth`)
- **THEN** the existing config entry's tokens SHALL be left unchanged

#### Scenario: Machine ID lookup is skipped when already known
- **WHEN** reauth authentication succeeds and the existing entry already records a machine ID
- **THEN** the flow SHALL NOT call the user profile endpoint
- **THEN** the entry SHALL retain its recorded machine ID

#### Scenario: Machine ID recovered when absent
- **WHEN** reauth authentication succeeds and the existing entry has no machine ID recorded
- **THEN** the flow SHALL fetch the user profile and store the discovered machine ID on the entry
