## ADDED Requirements

### Requirement: User step collects only email and password
The config flow SHALL present a form requesting only the user's PerfectDraft account email and password. No API keys, tokens, or technical fields SHALL be shown.

#### Scenario: User enters credentials
- **WHEN** the user opens the PerfectDraft integration setup
- **THEN** the config flow SHALL show a form with fields for email (string) and password (string, secret)
- **THEN** no other fields SHALL be present

### Requirement: External step for reCAPTCHA token generation
After credential entry, the config flow SHALL use HA's external step mechanism to open a browser page that generates a reCAPTCHA v3 token invisibly.

#### Scenario: reCAPTCHA external step initiated
- **WHEN** the user submits their email and password
- **THEN** the config flow SHALL transition to an external step
- **THEN** the external step SHALL serve or direct to an HTML page that loads Google reCAPTCHA v3 JS with site key `6LdrqmApAAAAAB_kTEHVnx9pua3TMurf4i75a-aQ`
- **THEN** the page SHALL generate a token invisibly (no user interaction beyond opening the page)
- **THEN** the page SHALL post the token back to the HA callback endpoint to resume the flow

#### Scenario: reCAPTCHA generation fails
- **WHEN** the reCAPTCHA JS fails to load or generate a token (network error, blocked)
- **THEN** the HTML page SHALL display an error message instructing the user to check network access to google.com

### Requirement: Authentication validation during setup
The config flow SHALL validate credentials by calling the PerfectDraft API before creating the config entry.

#### Scenario: Successful authentication
- **WHEN** the reCAPTCHA token is received and the API accepts the sign-in
- **THEN** the config flow SHALL store email, and the returned tokens (access, id, refresh) in the config entry data
- **THEN** the config flow SHALL NOT store the plaintext password beyond the initial sign-in call
- **THEN** the config entry SHALL be created with a title derived from the user's email or machine name

#### Scenario: Authentication failure
- **WHEN** the API rejects the credentials
- **THEN** the config flow SHALL show an error ("Invalid email or password") and return to the user step

#### Scenario: API unreachable
- **WHEN** the API is unreachable during setup
- **THEN** the config flow SHALL show an error ("Cannot connect to PerfectDraft service") and allow retry

### Requirement: Options flow for polling interval
The integration SHALL provide an OptionsFlow that allows the user to change the polling interval after setup.

#### Scenario: User adjusts polling interval
- **WHEN** the user opens integration options for PerfectDraft
- **THEN** a form SHALL be shown with a polling interval field (integer, seconds)
- **THEN** the default SHALL be 900 (15 minutes)
- **THEN** the minimum SHALL be 60 (1 minute)
- **THEN** changing the value SHALL take effect on the next coordinator refresh cycle

### Requirement: Reauth flow for expired refresh tokens
The integration SHALL support HA's reauth mechanism when the refresh token becomes invalid.

#### Scenario: Reauth triggered
- **WHEN** the coordinator detects that token refresh has failed (refresh token expired)
- **THEN** it SHALL trigger HA's reauth flow
- **THEN** the reauth flow SHALL repeat the email/password + reCAPTCHA external step sequence
- **THEN** on success, the config entry SHALL be updated with new tokens

### Requirement: Unique ID prevents duplicate entries
The config flow SHALL set a unique ID based on the user's account to prevent duplicate integrations for the same account.

#### Scenario: Duplicate prevention
- **WHEN** a user attempts to add the integration with an email that is already configured
- **THEN** the config flow SHALL abort with a message indicating the account is already set up
