## 1. Extract temperature logic into an HA-free module

- [x] 1.1 Create `custom_components/perfectdraft/temperature.py` with a docstring stating that it deliberately avoids Home Assistant imports so it can be unit-tested standalone, mirroring `keg_detection.py`
- [x] 1.2 Define `TEMP_MIN_PLAUSIBLE = -20.0` and `TEMP_MAX_PLAUSIBLE = 50.0` with a comment explaining that -128 is `0x80` read as a signed int8 by an uninitialised probe
- [x] 1.3 Implement `plausible_temperature(value)` returning a float when the value coerces and falls inside the inclusive range, else `None`; catch `TypeError` and `ValueError` from the coercion
- [x] 1.4 Implement `beer_temperature(details)` applying the fallback chain: plausible non-zero `displayedBeerTemperatureInCelsius`, else plausible `temperature`, else `None`
- [x] 1.5 Confirm an implausible displayed value falls through to the fallback field rather than short-circuiting to `None`

## 2. Wire the module into the sensor

- [x] 2.1 Import `beer_temperature` in `sensor.py` alongside the existing `keg_detection` import
- [x] 2.2 Reduce `_get_temperature()` to `return beer_temperature(_get_details(data))`
- [x] 2.3 Verify the `temperature` entry in `SENSOR_DESCRIPTIONS` is untouched — unit, device class, state class, precision, and `value_fn` wiring all unchanged
- [x] 2.4 Confirm no `available` override is added to `PerfectDraftSensor`, so a filtered reading surfaces as `unknown` rather than `unavailable`

## 3. Tests

- [x] 3.1 Create `tests/test_temperature.py` following the `sys.path` and `unittest` pattern from `tests/test_keg_detection.py`
- [x] 3.2 Cover a normal reading returned from the displayed field
- [x] 3.3 Cover `-128` in the displayed field with no usable fallback, asserting `None`
- [x] 3.4 Cover `-128` in the displayed field with a plausible `temperature` fallback, asserting the fallback value is returned
- [x] 3.5 Cover `-128` in both fields, asserting `None`
- [x] 3.6 Cover the existing `0` sentinel on the displayed field still falling through to the fallback
- [x] 3.7 Cover both fields absent, asserting `None`
- [x] 3.8 Cover a non-numeric value, asserting `None` and no raised exception
- [x] 3.9 Cover the range boundaries: -20.0 and 50.0 accepted, -20.1 and 50.1 rejected
- [x] 3.10 Run `python3 -m unittest discover -s tests -p 'test_temperature.py'` and confirm it passes without Home Assistant installed — 15 tests, all passing
- [x] 3.11 Run `python3 -m unittest discover -s tests -p 'test_keg_detection.py'` to confirm no regression in the other harness-free suite — 11 tests, all passing

## 4. Documentation and close-out

- [x] 4.1 Record the long-term-statistics caveat for the release notes. The repository has no `CHANGELOG.md`; release notes are written on the GitHub release, so the wording is carried in the PR description and must be copied into the release when this ships: the fix stops new sentinel samples but does not rewrite statistics already recorded, which users must clear via Developer Tools → Statistics.
- [x] 4.3 Run `openspec validate filter-temperature-sentinels` and confirm the change is still valid

### Awaiting maintainer go-ahead (public repository actions)

- [ ] 4.2 File the two deferred follow-ups as separate issues: the `!= 0` check discarding a genuine 0 °C reading, and whether `details.temperature` is the measurement or an echo of the setpoint
- [ ] 4.4 Reply on [issue #4](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/issues/4) explaining the range-based fix, the `unknown` rather than `unavailable` choice, and the statistics cleanup step
