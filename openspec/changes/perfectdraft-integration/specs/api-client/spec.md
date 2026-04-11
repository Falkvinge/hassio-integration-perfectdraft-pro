## ADDED Requirements

### Requirement: Async HTTP client for PerfectDraft API
The integration SHALL provide an async API client class that communicates with `https://api.perfectdraft.com` using `aiohttp`. All HTTP methods SHALL be async. The client SHALL use HA's `async_get_clientsession` for connection management.

#### Scenario: Client initialization
- **WHEN** the API client is instantiated with an `aiohttp.ClientSession`
- **THEN** it SHALL store the session and set the base URL to `https://api.perfectdraft.com`
- **THEN** it SHALL include the header `x-api-key: cAyzERqthCJXYVExjNAhr9CzE8ncLN2cQK3WGK10` on authentication requests

### Requirement: Sign-in with reCAPTCHA token
The client SHALL authenticate by POSTing to `/authentication/sign-in` with email, password, recaptchaToken, and recaptchaAction fields. The x-api-key SHALL be sent as a header.

#### Scenario: Successful sign-in
- **WHEN** the client calls `authenticate(email, password, recaptcha_token)`
- **THEN** it SHALL POST to `/authentication/sign-in` with JSON body `{ email, password, recaptchaToken, recaptchaAction: "Android_recaptchaThatWorks/login" }`
- **THEN** it SHALL store the returned `AccessToken`, `IdToken`, and `RefreshToken`

#### Scenario: Sign-in with invalid credentials
- **WHEN** the API returns a non-2xx status for sign-in
- **THEN** the client SHALL raise an `AuthenticationError`

#### Scenario: Sign-in with rejected reCAPTCHA
- **WHEN** the API rejects the reCAPTCHA token
- **THEN** the client SHALL raise an `AuthenticationError` with a message indicating reCAPTCHA failure

### Requirement: Token refresh
The client SHALL support refreshing an expired access token using the stored refresh token, without requiring a new reCAPTCHA.

#### Scenario: Successful token refresh
- **WHEN** the client calls `refresh_access_token(refresh_token)`
- **THEN** it SHALL request a new access token from the API using the refresh token
- **THEN** it SHALL update the stored access token (and refresh token if a new one is returned)

#### Scenario: Refresh token expired or invalid
- **WHEN** the refresh attempt returns an authentication error
- **THEN** the client SHALL raise an `AuthenticationError` to signal that full re-authentication is needed

### Requirement: Fetch user profile and machine IDs
The client SHALL retrieve the user's profile and associated machine identifiers.

#### Scenario: Successful profile fetch
- **WHEN** the client calls `get_user_profile()`
- **THEN** it SHALL GET `/api/me` with the `x-access-token` header set to the current access token
- **THEN** it SHALL return the response containing at minimum the machine ID(s)

#### Scenario: Access token expired during profile fetch
- **WHEN** the API returns 401 Unauthorized
- **THEN** the client SHALL attempt a token refresh and retry the request once
- **THEN** if the retry also fails, it SHALL raise an `AuthenticationError`

### Requirement: Fetch machine details
The client SHALL retrieve the full status of a specific PerfectDraft machine.

#### Scenario: Successful machine details fetch
- **WHEN** the client calls `get_machine_details(machine_id)`
- **THEN** it SHALL GET `/api/perfectdraft_machines/{machine_id}` with the access token header
- **THEN** it SHALL return the full response data (temperature, volume/remaining, keg info, expiry, image URL, etc.)

#### Scenario: Access token expired during machine fetch
- **WHEN** the API returns 401 Unauthorized
- **THEN** the client SHALL attempt a token refresh and retry the request once

### Requirement: Error handling and rate-limit resilience
The client SHALL handle API errors gracefully and avoid triggering Imperva WAF bans.

#### Scenario: HTTP error response
- **WHEN** the API returns a 4xx or 5xx status (other than 401)
- **THEN** the client SHALL raise a `PerfectDraftApiError` with the status code and response body

#### Scenario: Connection failure
- **WHEN** the HTTP request fails due to network error or timeout
- **THEN** the client SHALL raise a `PerfectDraftConnectionError`

#### Scenario: Rate limiting
- **WHEN** the API returns 429 Too Many Requests
- **THEN** the client SHALL raise a `PerfectDraftApiError` and NOT retry immediately
