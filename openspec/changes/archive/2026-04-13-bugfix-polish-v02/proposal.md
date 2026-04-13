## Why

The v0.1 integration proved the concept — PerfectDraft Pro talks to Home Assistant. But it has a showstopper bug (dies after 1 hour), missing HACS compliance (can't be installed via HACS), no branding, and rough onboarding UX. This changeset makes it a proper, installable, self-sustaining integration.

## What Changes

- **CRITICAL BUG**: Fix Cognito token refresh crash — `aiohttp` rejects the `application/x-amz-json-1.1` content type from Cognito's response, causing all sensors to go undefined after the 1-hour access token expires
- **HACS compliance**: Add `README.md` with setup instructions (including the token generation command), fix `manifest.json` documentation URL to point at the actual repo, verify repo structure passes HACS validation
- **Integration icon**: Add `brand/` directory with PerfectDraft icon extracted from the official app, so HA shows the brand icon instead of "icon not available"
- **Config flow UX**: Fix the MALFORMED_ARGUMENT translation error on the token step (curly braces in description parsed as placeholders) — already worked around but needs the description to actually contain the console command or a clear reference to it
- **Keg freshness sensor**: Track keg insertion locally (detect when `numberOfPoursSinceStartup` resets to 0 / `kegVolume` jumps to ~6L) and expose a "Days Fresh" countdown sensor (30-day expiry)
- **Version bump**: `manifest.json` version to `0.2.0`

## Capabilities

### New Capabilities
- `keg-freshness`: Client-side keg insertion tracking and freshness countdown sensor using HA's RestoreEntity for persistence across restarts

### Modified Capabilities
- `hacs-packaging`: Add README.md, fix documentation URL, add brand/ directory with icon
- `config-flow`: Fix translation string for token step, improve onboarding UX
- `api-client`: Fix Cognito refresh content-type handling

## Impact

- **Bug fix**: Resolves integration dying after 1 hour (Cognito refresh)
- **New file**: `README.md` at repo root
- **New file**: `custom_components/perfectdraft/brand/icon.png`
- **Modified**: `manifest.json` (version bump, URL fix)
- **Modified**: `api.py` (one-line fix: `content_type=None` on Cognito response parsing)
- **Modified**: `strings.json` / `translations/en.json` (token step description)
- **Modified**: `sensor.py` (new keg freshness sensor with RestoreEntity)
- **No breaking changes**: Existing config entries continue to work
