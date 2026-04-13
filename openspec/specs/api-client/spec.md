## Requirements

### Requirement: Async HTTP client
The integration SHALL provide an async API client class (`PerfectDraftApiClient`) that communicates with `https://api.perfectdraft.com` using `aiohttp.ClientSession`. All HTTP methods SHALL be async.

#### Scenario: Client initialization
- **WHEN** the API client is instantiated with an `aiohttp.ClientSession`
- **THEN** it SHALL store the session and set the base URL to `https://api.perfectdraft.com`

### Requirement: Sign-in with reCAPTCHA token
The client SHALL authenticate by POSTing to `/authentication/sign-in` with email, password, recaptchaToken, and recaptchaAction fields. The `x-api-key` SHALL be sent as a header. The `recaptchaAction` SHALL be `Magento/login`.

#### Scenario: Successful sign-in
- **WHEN** the client calls `authenticate(email, password, recaptcha_token)`
- **THEN** it SHALL POST to `/authentication/sign-in` with the correct payload and `x-api-key` header
- **THEN** it SHALL store the returned `AccessToken`, `IdToken`, and `RefreshToken`

#### Scenario: Sign-in failure
- **WHEN** the API returns 400, 401, or 403
- **THEN** the client SHALL raise `AuthenticationError` with the status and response body

### Requirement: Token refresh via Cognito
The client SHALL refresh expired access tokens by calling AWS Cognito directly at `https://cognito-idp.eu-west-1.amazonaws.com/`, bypassing the API gateway and reCAPTCHA. The Cognito client ID is `57ddq2ppqg2jcpup06r2g1deur`.

#### Scenario: Successful token refresh
- **WHEN** the client calls `refresh_access_token()`
- **THEN** it SHALL POST to Cognito with `AuthFlow: REFRESH_TOKEN_AUTH` and the stored refresh token
- **THEN** it SHALL parse the response with `content_type=None` to accept `application/x-amz-json-1.1`
- **THEN** it SHALL update the stored access token and ID token
- **THEN** the original refresh token SHALL remain unchanged (Cognito does not rotate it)

#### Scenario: Refresh token expired
- **WHEN** Cognito returns 400 or 401
- **THEN** the client SHALL raise `AuthenticationError`

#### Scenario: No refresh token available
- **WHEN** `refresh_access_token()` is called without a stored refresh token
- **THEN** the client SHALL raise `AuthenticationError`

### Requirement: Authenticated API requests with auto-retry
The client SHALL make authenticated requests with automatic 401 retry via token refresh.

#### Scenario: Successful request
- **WHEN** the client makes an API request
- **THEN** it SHALL include `x-api-key` and `x-access-token` headers

#### Scenario: 401 triggers refresh and retry
- **WHEN** the API returns 401
- **THEN** the client SHALL call `refresh_access_token()`, update the header, and retry once
- **THEN** if the retry also returns 401, it SHALL raise `AuthenticationError`

#### Scenario: Rate limiting
- **WHEN** the API returns 429
- **THEN** the client SHALL raise `PerfectDraftApiError` without retrying

#### Scenario: Network failure
- **WHEN** the HTTP request fails due to `aiohttp.ClientError`
- **THEN** the client SHALL raise `PerfectDraftConnectionError`

### Requirement: Fetch user profile
The client SHALL retrieve the user profile including machine IDs via `GET /api/me`.

#### Scenario: Profile response
- **WHEN** the client calls `get_user_profile()`
- **THEN** it SHALL return the JSON response containing `perfectdraftMachines` array with machine `id` fields

### Requirement: Fetch machine details
The client SHALL retrieve full machine telemetry via `GET /api/perfectdraft_machines/{machine_id}`.

#### Scenario: Machine details response
- **WHEN** the client calls `get_machine_details(machine_id)`
- **THEN** it SHALL return the JSON response containing `details` (temperature, kegVolume, connectedState, doorClosed, numberOfPoursSinceStartup, volumeOfLastPour, firmwareVersion, serialNumber) and `setting` (mode, temperature, boost)
