## MODIFIED Requirements

### Requirement: Sign-in with reCAPTCHA token
The client SHALL authenticate by calling AWS Cognito `InitiateAuth` at `https://cognito-idp.eu-west-1.amazonaws.com/` with `AuthFlow: USER_PASSWORD_AUTH`, the Cognito client ID, and the email and password as `USERNAME` and `PASSWORD`. `ClientMetadata` SHALL carry `recaptchaToken`, `recaptchaAction: Magento/login`, and `domain: https://www.perfectdraft.com`, all three of which PerfectDraft's PreAuthentication check requires. The client SHALL NOT sign in through `api.perfectdraft.com/authentication/sign-in`, which does not forward `domain`.

#### Scenario: Successful sign-in
- **WHEN** the client calls `authenticate(email, password, recaptcha_token)`
- **THEN** it SHALL POST an `InitiateAuth` request to Cognito with `Content-Type: application/x-amz-json-1.1` and `X-Amz-Target: AWSCognitoIdentityProviderService.InitiateAuth`
- **THEN** the request SHALL carry the `ClientMetadata` fields listed above
- **THEN** it SHALL parse the response with `content_type=None` to accept `application/x-amz-json-1.1`
- **THEN** it SHALL store the `AccessToken`, `IdToken`, and `RefreshToken` from `AuthenticationResult`

#### Scenario: Challenge instead of tokens
- **WHEN** Cognito answers 200 without a complete `AuthenticationResult`, for example with a `ChallengeName`
- **THEN** the client SHALL raise `AuthenticationError`, carrying the challenge name as its error type when present
- **THEN** no stored token SHALL change

#### Scenario: Sign-in failure
- **WHEN** Cognito returns 400, 401, or 403
- **THEN** the client SHALL raise `AuthenticationError` with the status and response body
- **THEN** the error SHALL expose the Cognito error type (`__type`, without any namespace prefix) and the human-readable message, when the body supplies them

#### Scenario: Rejection is classified
- **WHEN** a sign-in is rejected with error type `NotAuthorizedException` or `UserNotFoundException`
- **THEN** the error SHALL classify as a credentials failure
- **WHEN** a sign-in is rejected with error type `UserLambdaValidationException`
- **THEN** the error SHALL classify as a verification token failure
- **WHEN** a sign-in is rejected with any other error type, or none
- **THEN** the error SHALL classify as an other failure

#### Scenario: Unreadable rejection body
- **WHEN** a rejection body is not JSON, such as an HTML error page
- **THEN** the client SHALL still raise `AuthenticationError`, with no error type and a reason truncated to at most 200 characters

#### Scenario: Other sign-in failures
- **WHEN** Cognito returns any other non-200 status
- **THEN** the client SHALL raise `PerfectDraftApiError`
- **WHEN** the request fails due to `aiohttp.ClientError`
- **THEN** the client SHALL raise `PerfectDraftConnectionError`

#### Scenario: Secrets are not logged
- **WHEN** sign-in succeeds or fails
- **THEN** the password, the verification token, and the issued tokens SHALL NOT be logged
