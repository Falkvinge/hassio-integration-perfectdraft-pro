## 1. Worktree

- [x] 1.1 `scripts/agent-worktree.sh create fix-cognito-signin` and confirm `.worktree/fix-cognito-signin/.agent-lock` exists on branch `agent/fix-cognito-signin`

## 2. API client sign-in

- [x] 2.1 Add `RECAPTCHA_DOMAIN = "https://www.perfectdraft.com"` to `const.py`; drop `RECAPTCHA_ACTION_SIGN_IN` from `api.py` in favour of `const.RECAPTCHA_ACTION`, and move `COGNITO_IDP_URL` alongside if it reads better; verify `rg RECAPTCHA_ACTION_SIGN_IN` finds nothing
- [x] 2.2 Give `AuthenticationError` optional `code` and `reason`, a `kind` property (`credentials` / `token` / `other`, per the design table) and a never-empty `display_reason` (trailing period stripped, at most 200 chars); existing single-argument raises still work
- [x] 2.3 Rewrite `authenticate()` as Cognito `InitiateAuth` `USER_PASSWORD_AUTH` with `ClientMetadata {recaptchaToken, recaptchaAction, domain}`; parse with `content_type=None`; read tokens from `AuthenticationResult`; raise `AuthenticationError` (code = `ChallengeName`) when the result is missing or incomplete; parse `__type` / `message` from rejection bodies, tolerating namespaced types and non-JSON bodies; log no secrets
- [x] 2.4 Add `tests/test_api_authenticate.py` (stdlib-only, loads `api.py` without Home Assistant, fake session) covering every scenario in the `api-client` delta; verify `python3 -m unittest tests.test_api_authenticate` passes

## 3. Config flow errors

- [x] 3.1 In `async_step_token`, map `err.kind` to `token_rejected` / `invalid_credentials` / `invalid_auth`; on `invalid_credentials` re-show the `user` form (setup) or `reauth_confirm` form (reauth) with the error instead of the token form
- [x] 3.2 Pass `description_placeholders={"reason": ...}` on every `async_show_form` for `user`, `reauth_confirm` and `token` (empty string when there is no error)
- [x] 3.3 In `strings.json` and `translations/en.json`, reword `invalid_auth` to include `{reason}` and add `invalid_credentials` and `token_rejected`; verify the two files stay identical (`diff`)
- [x] 3.4 Extend `tests/test_config_flow.py`: one test per error key (setup and reauth), asserting the form step, the error key and the `reason` placeholder; update `test_reauth_bad_token_keeps_old_tokens` for the new key; add a check that every `errors["base"]` value in `config_flow.py` exists in both translation files; verify `.venv-test/bin/pytest tests/` passes (harness bumped to 0.13.375 / core 2026.10.4, see branch commit)

## 4. README

- [x] 4.1 Keep step 2 to one command that logs the token and adds a "Click THIS BLACK BOX to copy" button using `navigator.clipboard.writeText` (DevTools `copy()` cannot copy an async result in Firefox or Chromium, and Chromium truncates `prompt()` defaults at 2,000 chars); test in Firefox and Chrome/Edge that the clipboard receives the full token; reword steps 4–5 to "paste it"; add one sentence to run it once at the console prompt (not as a Live expression) and a fallback line using `console.log(t)`; verify the snippet runs in a browser console on the en-gb login page and the clipboard holds a ~2,600-char token

## 5. On-device verification and version

- [x] 5.1 Bump `manifest.json` to 0.3.5 (shared with `add-keg-48180`, which must not bump it again)
- [ ] 5.2 (DEFERRED 2026-11-07 by maintainer; no time for a reinstall) Install the branch build on Home Assistant and add the integration from scratch with a fresh README token; confirm the entry is created and sensors populate
- [ ] 5.3 (DEFERRED with 5.2) With a deliberately wrong password, confirm the flow returns to the credentials form showing `invalid_credentials` and Cognito's reason; with a stale (>2 min) token, confirm `token_rejected` on the token form
- [ ] 5.4 (DEFERRED with 5.2) Trigger a reauth on the existing entry and confirm it succeeds; if a keg is fitted, also confirm Keg Freshness keeps its countdown and clear that TODO in `PROJECT_HYGIENE.md`
- [x] 5.5 Run the full suite (`.venv-test/bin/pytest tests/` and `python3 -m unittest discover -s tests`) and confirm green

## Workflow follow-up

- Release jointly with `add-keg-48180`: integration v0.3.5 and card v0.4.3, published together. Release notes credit cesa030 (root cause and fix in #11) and brettjenkins (fork that confirmed it).
- After the release is live, comment on #11 with the release link and close it.
- #12 and #13 are closed as duplicates of #11 (each with a thank-you comment) ahead of the release; post the release link there too.
- Archive per `AGENTS.md` (merge, push, sync `api-client` and `config-flow` specs, archive, remove worktree and branch).
