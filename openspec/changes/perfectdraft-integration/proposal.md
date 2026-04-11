## Why

There is no working Home Assistant integration for the PerfectDraft Pro beer dispenser. Several community attempts exist but all fail due to incorrect reCAPTCHA handling, synchronous API calls, missing refresh-token logic, and broken HACS packaging. Users want to see keg status (brand, remaining volume, temperature, freshness) on their HA dashboards and use it in automations.

## What Changes

- New HACS-installable custom integration `perfectdraft` for Home Assistant
- Config flow that collects only email + password, handling reCAPTCHA transparently via an external browser step
- Async API client against `https://api.perfectdraft.com` with token refresh
- `DataUpdateCoordinator` for single-poll data sharing across entities (prevents IP bans from over-polling)
- Sensor entities: temperature, percent remaining, days until expiry, current keg name
- Image entity: keg artwork
- Configurable polling interval via OptionsFlow (default 15 min)
- Device-based entity model (one HA device per PerfectDraft machine) to prepare for future multi-machine support

## Capabilities

### New Capabilities
- `api-client`: Async HTTP client for the PerfectDraft cloud API — authentication (sign-in with reCAPTCHA, token refresh), machine discovery, machine status polling
- `config-flow`: Home Assistant config flow with email/password entry and browser-based reCAPTCHA via external step; OptionsFlow for polling interval
- `entities`: HA sensor and image entities backed by a DataUpdateCoordinator — temperature, percent remaining, days to expiry, keg name, keg image
- `hacs-packaging`: Repository structure, manifest, and metadata for HACS installation

### Modified Capabilities

(none — greenfield project)

## Impact

- **New code**: Entire `custom_components/perfectdraft/` directory plus repo-root `hacs.json`
- **Dependencies**: `aiohttp` (already provided by HA core — no pip install needed)
- **External services**: PerfectDraft cloud API (`api.perfectdraft.com`), Google reCAPTCHA v3
- **Security surface**: User credentials stored in HA config entry (encrypted at rest by HA); API tokens stored in `hass.data` at runtime; reCAPTCHA site key is public and hardcoded
- **Rate-limit risk**: Imperva WAF protects the API; conservative polling + exponential backoff on errors required
