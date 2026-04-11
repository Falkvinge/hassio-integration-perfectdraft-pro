## 1. Repository scaffolding and HACS packaging

- [x] 1.1 Create `custom_components/perfectdraft/` directory with `__init__.py` and `const.py` (domain, API base URL, x-api-key, reCAPTCHA site key, default poll interval)
- [x] 1.2 Create `manifest.json` with all required HA + HACS fields (domain, name, version, config_flow, iot_class, codeowners, documentation, issue_tracker)
- [x] 1.3 Create `hacs.json` at repository root with name, render_readme, homeassistant minimum version
- [x] 1.4 Create `strings.json` and `translations/en.json` with config flow step titles, field labels, error messages, and options flow labels

## 2. API client

- [x] 2.1 Create `api.py` with `PerfectDraftApiClient` class — constructor takes `aiohttp.ClientSession`, stores base URL and API key
- [x] 2.2 Implement `authenticate(email, password, recaptcha_token)` — POST to `/authentication/sign-in`, return token triple, raise `AuthenticationError` on failure
- [x] 2.3 Implement `refresh_access_token(refresh_token)` — attempt token refresh, raise `AuthenticationError` if refresh token is invalid
- [x] 2.4 Implement `get_user_profile()` — GET `/api/me` with access token header, auto-retry on 401 via refresh
- [x] 2.5 Implement `get_machine_details(machine_id)` — GET `/api/perfectdraft_machines/{machine_id}` with access token header, auto-retry on 401 via refresh
- [x] 2.6 Define exception classes: `PerfectDraftApiError`, `PerfectDraftConnectionError`, `AuthenticationError` in `exceptions.py`

## 3. Config flow

- [x] 3.1 Create `config_flow.py` with `PerfectDraftConfigFlow` — `async_step_user` shows email + password form
- [x] 3.2 Implement external step for reCAPTCHA — `async_step_recaptcha` initiates external step, `async_step_recaptcha_done` receives the token
- [x] 3.3 Create `static/recaptcha.html` — loads reCAPTCHA v3 JS with the site key, generates token invisibly, posts back to HA callback URL
- [x] 3.4 Register an HA view to serve `recaptcha.html` and handle the callback (post token back into the config flow)
- [x] 3.5 Implement auth validation — after reCAPTCHA token received, call API `authenticate()`, on success create config entry with tokens, on failure show error and return to user step
- [x] 3.6 Set unique ID from user email (or account ID from API response) and call `_abort_if_unique_id_configured`
- [x] 3.7 Implement `async_step_reauth` — re-authenticate flow for expired refresh tokens (email/password + reCAPTCHA again)
- [x] 3.8 Implement `OptionsFlowHandler` — form with polling interval (integer seconds, default 900, min 60)

## 4. Data coordinator

- [x] 4.1 Create `coordinator.py` with `PerfectDraftDataUpdateCoordinator` extending `DataUpdateCoordinator`
- [x] 4.2 Implement `_async_update_data` — call `get_user_profile()` to get machine ID, then `get_machine_details(machine_id)`, return raw response dict
- [x] 4.3 Handle `AuthenticationError` in update — trigger config entry reauth flow
- [x] 4.4 Handle `PerfectDraftApiError` / `PerfectDraftConnectionError` — raise `UpdateFailed`
- [x] 4.5 Support dynamic interval — read from config entry options, update interval when options change

## 5. Integration setup

- [x] 5.1 Implement `async_setup_entry` in `__init__.py` — create API client, create coordinator, store in `hass.data`, forward to sensor + image platforms
- [x] 5.2 Implement `async_unload_entry` — clean up `hass.data`, unload platforms
- [x] 5.3 Implement `async_migrate_entry` stub for future config entry version changes
- [x] 5.4 Listen for options updates — reload coordinator interval when options change

## 6. Sensor entities

- [x] 6.1 Create `sensor.py` with base `PerfectDraftSensorEntity` extending `CoordinatorEntity` + `SensorEntity` — shared DeviceInfo, unique ID pattern
- [x] 6.2 Implement `PerfectDraftTemperatureSensor` — device_class TEMPERATURE, unit °C, state_class MEASUREMENT, reads temperature from coordinator data
- [x] 6.3 Implement `PerfectDraftPercentRemainingSensor` — unit %, state_class MEASUREMENT, icon mdi:keg, reads volume/remaining from coordinator data
- [x] 6.4 Implement `PerfectDraftDaysToExpirySensor` — unit d, icon mdi:calendar-clock, reads expiry from coordinator data
- [x] 6.5 Implement `PerfectDraftKegNameSensor` — string state, icon mdi:beer, reads keg name/brand from coordinator data
- [x] 6.6 Handle "no keg loaded" state — sensors report None/unavailable when no keg is present

## 7. Image entity

- [x] 7.1 Create `image.py` with `PerfectDraftKegImage` extending `CoordinatorEntity` + `ImageEntity`
- [x] 7.2 Implement image URL sourcing from coordinator data — serve the keg artwork URL from the API response
- [x] 7.3 Handle missing image — report unavailable when no image URL in data

## 8. Integration testing and polish

- [ ] 8.1 Manually test full flow: add integration → reCAPTCHA step → auth → entities appear with real data
- [ ] 8.2 Verify HACS installation: add repo as custom repository in HACS, confirm it downloads and installs correctly
- [ ] 8.3 Verify options flow: change polling interval, confirm coordinator respects new interval
- [ ] 8.4 Verify reauth flow: invalidate tokens, confirm HA prompts for re-authentication
- [ ] 8.5 Document actual API response field names discovered during testing in code comments and update specs if needed
