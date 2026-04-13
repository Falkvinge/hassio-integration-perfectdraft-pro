## Requirements

### Requirement: User step collects email and password
The config flow SHALL present a form requesting the user's PerfectDraft account email and password as the first step.

#### Scenario: User enters credentials
- **WHEN** the user opens the PerfectDraft integration setup
- **THEN** the config flow SHALL show a form with fields for email and password
- **THEN** submitting SHALL advance to the token step

### Requirement: Token step collects verification token
The config flow SHALL present a form requesting a reCAPTCHA verification token as the second step, with instructions linking to the README.

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
- **WHEN** authentication fails
- **THEN** the flow SHALL show an error and allow the user to retry with a fresh token

#### Scenario: API unreachable
- **WHEN** the API is unreachable
- **THEN** the flow SHALL show a connection error

### Requirement: Unique ID prevents duplicates
The config flow SHALL set a unique ID based on the user's email to prevent duplicate integrations.

#### Scenario: Duplicate prevention
- **WHEN** a user attempts to add the integration with an email that is already configured
- **THEN** the config flow SHALL abort

### Requirement: Reauth flow
The integration SHALL support HA's reauth mechanism when the refresh token expires.

#### Scenario: Reauth triggered
- **WHEN** the coordinator detects that token refresh has failed
- **THEN** HA SHALL prompt the user to re-authenticate
- **THEN** the reauth flow SHALL collect email, password, and a fresh token
- **THEN** on success, the config entry SHALL be updated with new tokens

### Requirement: Options flow for polling interval
The integration SHALL provide an OptionsFlow to change the polling interval.

#### Scenario: User adjusts polling interval
- **WHEN** the user opens integration options
- **THEN** a form SHALL show the current polling interval (default 900 seconds)
- **THEN** the minimum SHALL be 60 seconds
- **THEN** changes SHALL take effect on the next coordinator refresh cycle
