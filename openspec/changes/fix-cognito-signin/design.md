## Context

See proposal.md for why. Current state:

- `authenticate()` in `api.py` POSTs `{email, password, recaptchaToken, recaptchaAction}` with `x-api-key` to `api.perfectdraft.com/authentication/sign-in`, and reads `AccessToken`/`IdToken`/`RefreshToken` from the top level of the response.
- `refresh_access_token()` already calls Cognito `InitiateAuth` directly (`REFRESH_TOKEN_AUTH`, client `57ddq2ppqg2jcpup06r2g1deur`, no client secret). Gateway and refresh share nothing beyond the client ID.
- `config_flow.py` maps every `AuthenticationError` to `invalid_auth` on the token form. `exceptions.AuthenticationError` is a bare subclass with no fields.
- The perfectdraft.com shop now sends `metadata: { recaptcha: { token, domain: window.location.origin } }`. cesa030's testing in #11 established three things. The gateway drops `domain` whatever field name or header is used. Direct `USER_PASSWORD_AUTH` works with `ClientMetadata {recaptchaToken, recaptchaAction: "Magento/login", domain: "https://www.perfectdraft.com"}`. Action `login` instead of `Magento/login` fails with "Unable to obtain reCAPTCHA site settings".
- Re-checked on 2026-11-07 in a browser: the README snippet still yields a token (2,660 characters) on the en-gb login page. The page logs nothing to the console on its own.

## Goals / Non-Goals

**Goals:**

- Setup and reauth work again with a token generated per the README.
- A failed sign-in names the rejected input and the server's reason, so the next PerfectDraft-side change shows up as a readable message instead of "token may have expired".

**Non-Goals:**

- Detecting future PerfectDraft protocol changes automatically.
- Localised error text beyond `en`. The integration ships only `translations/en.json`.

## Decisions

**Call Cognito directly rather than keep the gateway.**
No request shape gets `domain` through the gateway, so it cannot be fixed on our side. Cognito `InitiateAuth` is already a dependency through token refresh, so this adds no new endpoint or trust relationship. The `x-api-key` header is unnecessary for Cognito and is dropped from sign-in only. Data requests still send it.

**Write our own implementation; do not merge or cherry-pick brettjenkins' fork.**
The fork is 48 commits ahead and 64 behind. Its sign-in commit also touches the reauth path we already rewrote in `fix-reauth-flow`, plus versioning and the manifest. We reimplement from the protocol cesa030 documented in #11, which is a few lines, and credit both of them in the release notes. The error classification follows the same idea as the fork. The error key names `token_rejected` and `invalid_credentials` match it, so users moving back from the fork see familiar messages.

**`domain` is a constant `https://www.perfectdraft.com`, independent of the shop country.**
The Lambda validates it as the origin the token was minted for. All country shops share the `www.perfectdraft.com` origin. cesa030 confirmed en-gb and de-de tokens both work with it. It sits in `const.py` next to `RECAPTCHA_SITE_KEY` and `RECAPTCHA_ACTION`. `api.py`'s duplicate `RECAPTCHA_ACTION_SIGN_IN` is dropped in favour of `const.RECAPTCHA_ACTION`.

**Classification lives on `AuthenticationError`, not in the config flow.**
`AuthenticationError(message, code=None, reason=None)` gains a `kind` property (`credentials` / `token` / `other`) and a `display_reason` that is never empty. Existing `AuthenticationError("...")` call sites, including refresh and the coordinator, keep working unchanged. The config flow maps `kind` to an error key and stays free of Cognito vocabulary.

| Cognito `__type` | kind | Error key | Form shown again |
|---|---|---|---|
| `NotAuthorizedException`, `UserNotFoundException` | credentials | `invalid_credentials` | user form (setup) or `reauth_confirm` (reauth) |
| `UserLambdaValidationException` | token | `token_rejected` | token form |
| anything else, a challenge name, or none | other | `invalid_auth` | token form |

`NotAuthorizedException` also covers "Password attempts exceeded". It still lands on the credentials form, and the reason text says what happened.

**A credentials failure returns to the credentials form.**
reCAPTCHA Enterprise tokens are single-use, so the token is spent either way. Asking for another token on the token form would only lead to the same rejection. The flow re-renders the user form (or `reauth_confirm`) with the error, and submitting it leads back to the token step as usual.

**The server's reason goes through `{reason}` in the error strings.**
Home Assistant fills error placeholders from `description_placeholders`. Every `async_show_form` for `user`, `reauth_confirm` and `token` passes `{"reason": ...}`, with an empty string when there is no error, so no form can render a literal `{reason}`. The reason is the Cognito `message`, with any trailing period removed (the string supplies punctuation) and truncated to 200 characters. It is also logged at error level, as today. The log contains the Cognito error body only, never the request.

**README: copy to the clipboard instead of printing the token.**
`copy()` is a DevTools console utility in Chrome, Edge, Firefox and Safari. The snippet becomes `….then(t => { copy(t); console.log('Token copied to clipboard') })`. Users no longer have to select a 2,600-character string, and nothing scrolls past. A sentence notes that the command should be run once at the console prompt, not as a "Live expression", which re-runs it continuously. That is the most likely explanation for #13's stream of tokens.

**Tests: stdlib-only for the client, existing harness for the flow.**
`tests/test_api_authenticate.py` loads `api.py` without Home Assistant and drives a fake session. It covers the request shape, success, a challenge, each rejection kind, non-JSON bodies, other statuses and `ClientError`. `tests/test_config_flow.py` gains one test per error key, covering the form each lands on and the placeholder. It also gains a check that every config error key used in `config_flow.py` exists in both translation files, mirroring the existing abort-reason check.

## Risks / Trade-offs

- **PerfectDraft changes the Lambda again.** The reason now reaches the UI, so the next break is diagnosable from a user's screenshot. Nothing else changes.
- **PerfectDraft disables `USER_PASSWORD_AUTH` on the app client.** Cognito would return `InvalidParameterException`, which surfaces as `invalid_auth` with the reason. There is no mitigation beyond reacting. The shop itself appears to rely on this flow.
- **We cannot test against the real service before release.** The stored refresh token on the dev host has expired. Mitigation: a manual sign-in through Home Assistant with the built branch before tagging (task group 5). It doubles as the reauth check owed in `PROJECT_HYGIENE.md` if a keg is fitted.
- **`copy()` is unavailable in some browser.** The README keeps a fallback line with the old `console.log(t)` form.

## Migration Plan

None. The config entry schema and stored token shape are unchanged. Installs whose refresh token is still valid never call `authenticate()` and see no difference. Rolling back to 0.3.4 restores a sign-in that is already broken, so there is no rollback that helps users. Fixes go forward.
