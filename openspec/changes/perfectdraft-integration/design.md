## Context

This is a greenfield Home Assistant custom integration for the PerfectDraft Pro beer dispenser. The PerfectDraft Pro connects to a cloud API at `api.perfectdraft.com` via the manufacturer's mobile app. The API is undocumented; all knowledge comes from community reverse-engineering (traffic sniffing, one partial HA integration attempt that never worked).

Known API surface (from community research):

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/authentication/sign-in` | POST | x-api-key header | Login with email, password, reCAPTCHA token |
| `/api/me` | GET | x-access-token | Get user profile + machine IDs |
| `/api/perfectdraft_machines/{id}` | GET | x-access-token | Get machine status (temp, keg, volume, etc.) |

Authentication returns `AccessToken`, `IdToken`, and `RefreshToken`. The refresh endpoint is not yet confirmed but is expected to exist (standard JWT pattern). The API is protected by Imperva WAF which bans IPs that make too many requests.

The reCAPTCHA is Google reCAPTCHA v3 (invisible, score-based). The site key `6LdrqmApAAAAAB_kTEHVnx9pua3TMurf4i75a-aQ` is public. A token must be generated client-side (in a browser) and sent with the sign-in request. Tokens expire in ~2 minutes.

## Goals / Non-Goals

**Goals:**
- Working HACS-installable integration that a user can set up with only email + password
- Transparent reCAPTCHA handling (user clicks through a browser step once at setup)
- Resilient token lifecycle: persist refresh token, re-auth only when refresh fails
- Conservative API usage via DataUpdateCoordinator with configurable interval
- Device-based entity model ready for future multi-machine support
- Expose: temperature, percent remaining, days to expiry, keg name, keg image

**Non-Goals:**
- Controlling the machine (setting temperature, etc.) — read-only for v1
- Multi-machine support in the UI (data model supports it; config flow doesn't enumerate)
- Offline/local API access (the machine only talks to the cloud)
- Custom Lovelace cards (standard entities work with stock cards)

## Decisions

### D1: reCAPTCHA via HA external step + static HTML page

**Choice**: Serve a small HTML file during config flow that loads the Google reCAPTCHA v3 JS, generates a token invisibly, and posts it back to HA via the external step callback mechanism.

**Alternatives considered**:
- *Ask user to paste token manually* — tokens expire in ~2 min, terrible UX, what the existing broken integration does
- *Headless reCAPTCHA solving* — violates Google ToS, unreliable, unnecessary since v3 is invisible
- *Skip reCAPTCHA entirely* — API requires it for sign-in, no way around it

**Rationale**: HA's `async_external_step` / `async_external_step_done` pattern is designed exactly for this. The user sees "Open your browser to complete setup", clicks, reCAPTCHA v3 solves invisibly (no checkbox), and the flow resumes. One-time during setup.

### D2: Token persistence and refresh strategy

**Choice**: Store `RefreshToken` in the config entry data (encrypted at rest by HA). On coordinator update, if AccessToken is expired or returns 401, attempt refresh. If refresh fails, trigger HA reauth flow (user re-does the reCAPTCHA step).

**Alternatives considered**:
- *Re-authenticate with reCAPTCHA on every token expiry* — requires browser interaction each time, unacceptable
- *Store tokens in a separate file* — HA config entries already handle encrypted persistence

**Rationale**: Standard pattern for HA integrations with OAuth-like auth. The reauth flow is HA's built-in mechanism for "your credentials stopped working, please fix."

### D3: Single DataUpdateCoordinator, all entities share data

**Choice**: One `PerfectDraftDataUpdateCoordinator` per config entry. It polls `/api/me` → `/api/perfectdraft_machines/{id}` on a timer. All sensor and image entities read from `coordinator.data`.

**Alternatives considered**:
- *Each entity polls independently* — multiplies API calls, causes IP bans (this is what killed the existing integration's users)
- *Push/websocket* — API doesn't support it

**Rationale**: This is HA's recommended pattern (`DataUpdateCoordinator`). One poll cycle, shared data, built-in error handling and exponential backoff.

### D4: Device-per-machine entity model

**Choice**: Each PerfectDraft machine becomes an HA `Device`. All entities (sensors, image) are children of that device. The device is identified by `machine_id` from the API.

**Alternatives considered**:
- *Flat sensors with no device* — works but prevents future multi-machine and looks worse in the UI

**Rationale**: Even with single-machine support initially, the device model is trivial to set up and gives a much better UI experience (all sensors grouped under one device card). Adding multi-machine later is just a loop.

### D5: Configurable polling interval via OptionsFlow

**Choice**: Default 900 seconds (15 min). User can change via integration options in HA UI. Minimum 60 seconds to avoid rate limiting.

**Alternatives considered**:
- *Fixed interval* — user specifically wants to increase frequency during game sessions
- *Adaptive polling* — complex, premature for v1

**Rationale**: Simple, user-controllable, covers the "game night = more frequent polling" use case.

### D6: Async-only with aiohttp

**Choice**: Use `aiohttp.ClientSession` (provided by HA via `async_get_clientsession`) for all HTTP calls. No synchronous code.

**Alternatives considered**:
- *`requests` library in executor* — the existing broken integration does this; it's an anti-pattern in HA

**Rationale**: HA is async-first. Using `async_get_clientsession` also gets connection pooling and proper SSL handling for free.

### D7: Hardcode the x-api-key and reCAPTCHA site key

**Choice**: Both are constants in `const.py`. The user never sees or enters them.

**Rationale**: The x-api-key is static across all users (it identifies the app, not the user). The reCAPTCHA site key is public by definition. Asking users to find these was a major UX failure in the existing integration.

## Risks / Trade-offs

**[Undocumented API may change without notice]** → Pin behavior to known endpoints; log response shapes on first successful call for debugging; fail gracefully with clear error messages pointing to GitHub issues.

**[Imperva WAF rate limiting / IP bans]** → DataUpdateCoordinator with minimum 60s interval; exponential backoff on HTTP errors; never retry auth in a tight loop.

**[reCAPTCHA v3 score rejection]** → If Google gives a low score (bot suspicion), the token may be rejected by PerfectDraft's backend. Mitigation: clear error message in config flow asking user to retry. This is inherent to reCAPTCHA v3 and rare for real browser interactions.

**[Refresh token expiry unknown]** → We don't know the refresh token TTL. If it expires after days/weeks, the user will need to re-authenticate. HA's reauth flow handles this gracefully.

**[Machine details response shape unknown]** → The exact field names for keg info, volume remaining, expiry, and image URL are not confirmed. Implementation will need to probe the API and adapt. Design the coordinator to store the raw response and let entities pick fields, so field name changes only require entity-level fixes.

**[External step requires network access to Google]** → The HA instance needs outbound HTTPS to `www.google.com` for reCAPTCHA JS. This is standard for most HA setups but could fail on air-gapped networks. Non-goal to support air-gapped.
