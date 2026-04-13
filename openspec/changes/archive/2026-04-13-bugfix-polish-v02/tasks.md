## 1. Critical bug fix

- [x] 1.1 Fix Cognito refresh content-type: add `content_type=None` to `resp.json()` call in `api.py` `refresh_access_token()` method
- [x] 1.2 Verify fix with test harness: run token refresh and confirm no content-type error

## 2. HACS compliance

- [x] 2.1 Create `README.md` at repo root with: integration description, sensor list, installation instructions, token generation command (the `grecaptcha.enterprise.execute` one-liner), and a note that the token step is easier than it looks
- [x] 2.2 Fix `manifest.json`: update `documentation` and `issue_tracker` URLs to point at `https://git.falkvinge.net/rick/hassio-integration-perfectdraft-pro`
- [x] 2.3 Bump `manifest.json` version to `0.2.0`

## 3. Brand icon

- [x] 3.1 Create `custom_components/perfectdraft/brand/` directory
- [x] 3.2 Copy PerfectDraft glass icon from decompiled APK (`res/mipmap-xxxhdpi/ic_launcher.png`) to `brand/icon.png`
- [x] 3.3 Verify icon is 192x192 PNG with transparency (HA brand icon requirements)

## 4. Config flow UX

- [x] 4.1 Update token step description in `strings.json` and `translations/en.json` to reference the README for the console command, without curly braces or newlines that break HA's translation system

## 5. Keg freshness sensor

- [x] 5.1 Add `RestoreSensor` mixin to a new `PerfectDraftKegFreshnessSensor` class in `sensor.py`
- [x] 5.2 Implement keg insertion detection: watch for `numberOfPoursSinceStartup` dropping to 0 AND `kegVolume` > 5.5L
- [x] 5.3 Persist keg insertion timestamp via `RestoreEntity` extra stored data
- [x] 5.4 Expose "Keg Freshness" sensor: `30 - days_since_insertion`, unit `d`, icon `mdi:calendar-clock`, unavailable when no insertion date known
- [x] 5.5 Add entity name translation for the new sensor

## 6. Build and test

- [x] 6.1 Syntax-check all modified files
- [x] 6.2 Build zip, deploy to HA, verify: integration survives past 1 hour, icon shows, sensors named correctly, keg freshness sensor appears (manual — user)
- [x] 6.3 Commit and push as v0.2.0
