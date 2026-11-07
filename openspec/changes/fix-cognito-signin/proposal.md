## Why

Nobody can set up the integration or recover from a reauth prompt. Since PerfectDraft's October 2026 frontend update, every sign-in fails with `UserLambdaValidationException: PreAuthentication failed with error 'domain'`. PerfectDraft's Cognito PreAuthentication Lambda now requires a `domain` field in `ClientMetadata`, and the `api.perfectdraft.com/authentication/sign-in` gateway that `authenticate()` posts to does not forward it. Issue #11 has the root cause and a working fix from cesa030. #12 and #13 are the same failure.

The config flow made this hard to diagnose. Every authentication failure shows the same `invalid_auth` text, "Token may have expired (2 min limit) or credentials are wrong". So in #12 users regenerated tokens over and over for a failure no fresh token could fix.

## What Changes

- `PerfectDraftApiClient.authenticate()` signs in by calling Cognito `InitiateAuth` with `USER_PASSWORD_AUTH` directly. This is the endpoint token refresh already uses. `ClientMetadata` carries `recaptchaToken`, `recaptchaAction: Magento/login`, and `domain: https://www.perfectdraft.com`. The API gateway sign-in endpoint is no longer used.
- If Cognito answers with a challenge instead of tokens, sign-in fails with `AuthenticationError` rather than a `KeyError`.
- `AuthenticationError` carries the Cognito error type and message when the server supplies them.
- The config flow tells the user why sign-in failed:
  - A wrong email or password (`NotAuthorizedException`, `UserNotFoundException`) returns to the credentials form with `invalid_credentials`. This is the user form during setup and `reauth_confirm` during reauth.
  - A rejected verification token (`UserLambdaValidationException`) stays on the token form with `token_rejected`.
  - Anything else stays on the token form with `invalid_auth`.
  - All three show the server's reason.
- README step 2: the console snippet copies the token to the clipboard and prints a short confirmation. The user no longer has to select a 2,600-character string by hand. A note says to run it once at the console prompt.
- Integration version 0.4.4, synced with the companion card (both 0.4.4; major.minor in lockstep from here). It ships in one joint release with `add-keg-48180` and the companion card release.

Not in scope:

- Persisting Cognito-refreshed tokens back to the config entry. This is a separate TODO in `PROJECT_HYGIENE.md`.
- Automating token acquisition (an embedded browser, or a reCAPTCHA solver). The user still pastes a token generated on perfectdraft.com.
- Any change to token refresh. It already calls Cognito directly and is unaffected.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `api-client`: "Sign-in with reCAPTCHA token" moves from the gateway to Cognito `InitiateAuth`, with the required `ClientMetadata`. Failures carry the Cognito error type and reason, and a challenge response is a failure.
- `config-flow`: the "Invalid or expired token" scenario splits into three outcomes (credentials, token, other), each showing the server's reason. The reauth "authentication fails" scenario follows the same split.

## Impact

- `custom_components/perfectdraft/api.py`: `authenticate()`.
- `custom_components/perfectdraft/exceptions.py`: `AuthenticationError` gains optional `code` and `reason`.
- `custom_components/perfectdraft/const.py`: the reCAPTCHA domain constant. The sign-in action constant moves out of `api.py`.
- `custom_components/perfectdraft/config_flow.py`: error mapping in `async_step_token`, and a return to the credentials form.
- `custom_components/perfectdraft/strings.json`, `translations/en.json`: two new error keys. `invalid_auth` is reworded to include `{reason}`.
- `README.md`: the step 2 snippet and wording.
- `manifest.json`: 0.4.4.
- `tests/`: a new stdlib-only test module for `authenticate()`. `test_config_flow.py` gains tests for the three error paths.
- External: issues #11, #12 and #13. #12 and #13 are closed as duplicates of #11. #11 closes once the release ships. Credit goes to cesa030 for the root cause and fix, and to brettjenkins for the fork that confirmed it.
- No config entry migration. Stored tokens have the same shape, so existing installs with a valid refresh token are unaffected.
