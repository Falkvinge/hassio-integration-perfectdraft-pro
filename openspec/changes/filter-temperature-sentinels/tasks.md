## 1. Extract temperature logic into an HA-free module

- [ ] 1.1 Create `custom_components/perfectdraft/temperature.py` with a docstring stating that it deliberately avoids Home Assistant imports so it can be unit-tested standalone, mirroring `keg_detection.py`
- [ ] 1.2 Define `TEMP_MIN_PLAUSIBLE = -20.0` and `TEMP_MAX_PLAUSIBLE = 50.0` with a comment explaining that -128 is `0x80` read as a signed int8 by an uninitialised probe
- [ ] 1.3 Implement `plausible_temperature(value)` returning a float when the value coerces and falls inside the inclusive range, else `None`; catch `TypeError` and `ValueError` from the coercion
- [ ] 1.4 Implement `beer_temperature(details)` applying the fallback chain: plausible non-zero `displayedBeerTemperatureInCelsius`, else plausible `temperature`, else `None`
- [ ] 1.5 Confirm an implausible displayed value falls through to the fallback field rather than short-circuiting to `None`

## 2. Wire the module into the sensor

- [ ] 2.1 Import `beer_temperature` in `sensor.py` alongside the existing `keg_detection` import
- [ ] 2.2 Reduce `_get_temperature()` to `return beer_temperature(_get_details(data))`
- [ ] 2.3 Verify the `temperature` entry in `SENSOR_DESCRIPTIONS` is untouched — unit, device class, state class, precision, and `value_fn` wiring all unchanged
- [ ] 2.4 Confirm no `available` override is added to `PerfectDraftSensor`, so a filtered reading surfaces as `unknown` rather than `unavailable`

## 3. Tests

- [ ] 3.1 Create `tests/test_temperature.py` following the `sys.path` and `unittest` pattern from `tests/test_keg_detection.py`
- [ ] 3.2 Cover a normal reading returned from the displayed field
- [ ] 3.3 Cover `-128` in the displayed field with no usable fallback, asserting `None`
- [ ] 3.4 Cover `-128` in the displayed field with a plausible `temperature` fallback, asserting the fallback value is returned
- [ ] 3.5 Cover `-128` in both fields, asserting `None`
- [ ] 3.6 Cover the existing `0` sentinel on the displayed field still falling through to the fallback
- [ ] 3.7 Cover both fields absent, asserting `None`
- [ ] 3.8 Cover a non-numeric value, asserting `None` and no raised exception
- [ ] 3.9 Cover the range boundaries: -20.0 and 50.0 accepted, -20.1 and 50.1 rejected
- [ ] 3.10 Run `python3 -m unittest discover -s tests -p 'test_temperature.py'` and confirm it passes without Home Assistant installed
- [ ] 3.11 Run `python3 -m unittest discover -s tests -p 'test_keg_detection.py'` to confirm no regression in the other harness-free suite

## 4. Documentation and close-out

- [ ] 4.1 Note in the release notes that the fix stops new bad samples but does not rewrite existing long-term statistics, which must be cleared via Developer Tools → Statistics
- [ ] 4.2 File the two deferred follow-ups as separate issues: the `!= 0` check discarding a genuine 0 °C reading, and whether `details.temperature` is the measurement or an echo of the setpoint
- [ ] 4.3 Run `openspec validate filter-temperature-sentinels` and confirm the change is still valid
- [ ] 4.4 Reply on [issue #4](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/issues/4) explaining the range-based fix, the `unknown` rather than `unavailable` choice, and the statistics cleanup step
