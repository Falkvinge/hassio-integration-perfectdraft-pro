## Context

The v0.1 integration is functional but fragile. It authenticates, fetches machine data, and exposes 8 sensors. However, it crashes after 1 hour when the access token expires and the Cognito refresh response can't be parsed. It also can't be installed via HACS due to missing README and incorrect URLs, and shows no brand icon in the HA UI.

The codebase is small (~30KB of Python across 7 files) and well-structured with a DataUpdateCoordinator pattern. Changes are surgical.

## Goals / Non-Goals

**Goals:**
- Make the integration survive indefinitely without user intervention (fix token refresh)
- Make it installable via HACS custom repository
- Show the PerfectDraft brand icon in the HA UI
- Track keg freshness client-side since the API doesn't provide it
- Bump version to 0.2.0

**Non-Goals:**
- Keg name/image (API doesn't expose product details beyond an ID)
- Multi-machine support (data model already supports it; UI doesn't need changes yet)
- Custom Lovelace cards
- Automated reCAPTCHA (the console-command approach works and is one-time)

## Decisions

### D1: Cognito content-type fix

**Choice**: Pass `content_type=None` to `aiohttp`'s `resp.json()` call when parsing the Cognito response.

**Rationale**: Cognito returns `application/x-amz-json-1.1` as the content type. `aiohttp` defaults to only accepting `application/json`. The fix is a single parameter. Alternative would be to use `resp.text()` + `json.loads()`, but `content_type=None` is the idiomatic aiohttp approach.

### D2: Brand icon via brand/ directory

**Choice**: Place `icon.png` in `custom_components/perfectdraft/brand/` using the PerfectDraft glass icon extracted from the official APK.

**Rationale**: HA 2026.3+ supports local brand images in this directory. No need to submit to the home-assistant/brands repository. The icon is the official PerfectDraft glass silhouette from their app — recognizable and appropriate.

### D3: Keg freshness tracking via RestoreEntity

**Choice**: Detect new keg insertion when `numberOfPoursSinceStartup` resets to 0 (or drops significantly) AND `kegVolume` is near 6L. Store the insertion timestamp using HA's `RestoreEntity` mixin. Expose a "Keg Freshness" sensor showing days remaining out of 30.

**Alternatives considered**:
- *Use the /api/perfectdraft_machine_kegs endpoint* — returns all kegs globally (2M+), can't filter by machine, no insertion date per machine
- *Track via kegVolume jump only* — could false-positive on reconnection after offline period

**Rationale**: The PerfectDraft app calculates the 30-day countdown client-side. We replicate this logic. `RestoreEntity` persists the timestamp across HA restarts. The dual signal (pours reset + volume near full) is robust against edge cases.

### D4: README as primary documentation

**Choice**: Create a `README.md` at repo root with installation instructions, the token generation command, and sensor descriptions. Reference it from the config flow description.

**Rationale**: HACS requires a README. The token generation command contains curly braces that break HA's translation system, so it can't live in `strings.json`. The README is the natural home for setup instructions, and HACS renders it on the integration page.

### D5: Fix manifest.json URLs

**Choice**: Point `documentation` and `issue_tracker` at `https://git.falkvinge.net/rick/hassio-integration-perfectdraft-pro`.

**Rationale**: The current URLs point at a nonexistent GitHub repo. The actual repo is on git.falkvinge.net with split-horizon DNS (internal from the LAN, DMZ ingress externally).

## Risks / Trade-offs

**[Keg freshness resets on integration reinstall]** → `RestoreEntity` only persists within the same config entry. If the user removes and re-adds the integration, the keg insertion date is lost. Acceptable — it's a convenience sensor, not critical data.

**[30-day freshness assumption]** → PerfectDraft's official freshness period is 30 days for all kegs. If this changes per-keg in the future, we'd need product-specific data from the API (which doesn't currently exist).

**[Cognito refresh token longevity unknown]** → Standard Cognito default is 30 days. When it expires, the user needs to redo the console command via the reauth flow. The integration handles this gracefully via `ConfigEntryAuthFailed`.
