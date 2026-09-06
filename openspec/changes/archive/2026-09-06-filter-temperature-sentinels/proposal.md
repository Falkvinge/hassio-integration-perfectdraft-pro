## Why

When the machine's refrigeration first starts (for example on wake from standby), the temperature probe reports `-128` — `0x80` read as a signed 8-bit integer, the firmware's "not yet initialised" sentinel. The cloud API passes that value through verbatim and the integration reports it as a real measurement, polluting Home Assistant history graphs and long-term statistics until the probe settles ([issue #4](https://github.com/Falkvinge/hassio-integration-perfectdraft-pro/issues/4)).

## What Changes

- The temperature sensor SHALL reject implausible readings and report no value instead of a bogus measurement, so the state becomes `unknown` and is excluded from recorder statistics.
- Both temperature sources are validated. Today only `details.displayedBeerTemperatureInCelsius` is sanity-checked (against `0`); the `details.temperature` fallback is used unconditionally and would happily surface `-128`.
- The existing `!= 0` sentinel check on the displayed field is retained unchanged. It guards a different firmware's uninitialised value and is out of scope here; the known defect that it also discards a genuine 0 °C reading is recorded as a follow-up rather than fixed in this change.
- Unit tests are introduced for the temperature extractor. There is currently no test coverage for any sensor value function.

Not breaking: the sensor's unit, device class, state class, and entity ID are unchanged. Consumers already have to handle `unknown`, which the sensor can produce today when both API fields are absent.

## Capabilities

### New Capabilities

None. This tightens the behaviour of an existing sensor.

### Modified Capabilities

- `entities`: the **Temperature sensor** requirement gains a validity constraint. It currently mandates reporting whatever the API returns; it must instead mandate rejecting out-of-range sentinel values and reporting no value.

## Impact

- `custom_components/perfectdraft/temperature.py` — new module holding the plausibility range and the extraction logic, kept free of Home Assistant imports so it is testable without the harness (the same rationale as the existing `keg_detection.py`).
- `custom_components/perfectdraft/sensor.py` — `_get_temperature()` becomes a thin adapter over the new module.
- `tests/test_temperature.py` — new file, running under plain `unittest` like `tests/test_keg_detection.py`.
- No API client, coordinator, config flow, or translation changes.
- Users affected by the bug will still have `-128` samples in their existing long-term statistics. Those are not rewritten by this change and must be removed manually via Developer Tools → Statistics; the release notes need to say so.
