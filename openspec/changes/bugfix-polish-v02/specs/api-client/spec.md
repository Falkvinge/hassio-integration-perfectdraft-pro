## MODIFIED Requirements

### Requirement: Token refresh
The client SHALL support refreshing an expired access token using the stored refresh token via direct Cognito InitiateAuth.

#### Scenario: Successful token refresh
- **WHEN** the client calls `refresh_access_token()`
- **THEN** it SHALL POST to `https://cognito-idp.eu-west-1.amazonaws.com/` with the `REFRESH_TOKEN_AUTH` flow
- **THEN** it SHALL parse the response using `content_type=None` to accept `application/x-amz-json-1.1`
- **THEN** it SHALL update the stored access token and ID token

#### Scenario: Refresh token expired
- **WHEN** the Cognito refresh returns a 400/401 error
- **THEN** the client SHALL raise an `AuthenticationError` to trigger HA's reauth flow
