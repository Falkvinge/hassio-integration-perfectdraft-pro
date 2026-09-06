## Context

The integration is `cloud_polling`. It never speaks to the dispenser directly, so there is no byte-level decoding anywhere in the repository — `-128` is produced by the machine's firmware, relayed through PerfectDraft's backend, and arrives as a JSON number. We cannot fix it at the source; we can only refuse to believe it.

The entire current implementation is five lines:

```python
def _get_temperature(data: dict) -> float | None:
    val = _get_details(data).get("displayedBeerTemperatureInCelsius")
    if val is not None and val != 0:
        return float(val)
    val = _get_details(data).get("temperature")
    return float(val) if val is not None else None
```

The `!= 0` test is significant prior art: it is an existing sentinel filter for the same class of defect, presumably added when a firmware reported `0` before initialising. `-128` looks like a newer firmware's sentinel for the identical condition, which argues for generalising the guard that already exists rather than adding a parallel mechanism.

Constraints: no test coverage exists for any sensor value function, and we have exactly one recorded sample of the API payload (in `DISCOVERY.md`), in which `setting.temperature` and `details.temperature` are both `3` and therefore indistinguishable.

## Goals / Non-Goals

**Goals:**

- A sentinel reading never reaches the recorder as a measurement.
- Both temperature sources are validated, not just the displayed one.
- The extractor gains unit tests, establishing a pattern for testing the other value functions.

**Non-Goals:**

- Repairing `-128` samples already written to users' long-term statistics. Recorder surgery is out of scope; the release notes will point at Developer Tools → Statistics.
- Changing the `!= 0` behaviour, including its known defect of discarding a real 0 °C reading. Recorded as a follow-up.
- Determining whether `details.temperature` is the measurement or an echo of the setpoint. Recorded as a follow-up.
- Exposing the unused `setting.temperatureMin` / `temperatureMax` / Fahrenheit fields.

## Decisions

### Report `unknown`, not `unavailable`

The reporter asked for the entity to go unavailable. We return `None` from the value function instead, which Home Assistant renders as `unknown`.

Both are excluded from history graphs and long-term statistics, so both solve the stated problem. `unknown` is chosen because it is semantically accurate — the device is reachable and the coordinator poll succeeded, there is simply no valid reading yet — and because it matches how every other sensor in this integration signals missing data. Marking the entity unavailable would mean overriding the `available` property, which would falsely imply a connectivity failure and diverge from the established pattern.

The one entity that does override `available` is `PerfectDraftKegFreshnessSensor`, and the distinction is instructive: a keg with no known insertion date has no meaningful value *at all*, whereas a temperature sensor awaiting probe initialisation has a value that is merely temporarily absent.

### Validate by plausible range, not by matching `-128`

The issue suggests special-casing `-128`. A range check is preferred: it costs the same, and it also catches the other sentinels this firmware family evidently likes to emit (`0x7F` → `127`, `0xFF` → `-1` if a field is ever read unsigned, and whatever the next firmware invents). Hard-coding one magic number would leave us reopening this issue.

Bounds are `-20.0` to `50.0` inclusive. The reporter proposed `-50`/`+50`; the lower bound is tightened because a beer dispenser has no legitimate reading below `-20 °C`, and a narrower window catches more sentinel variants. The upper bound stays at `50 °C` to accommodate an unpowered machine sitting in a hot room. This is a judgement call, so the bounds are named module-level constants rather than inline literals, making them cheap to revise if a real reading is ever rejected.

### Filter in the extractor, not the entity

Putting the check in `PerfectDraftSensor.native_value` would either apply it to every sensor indiscriminately or require a per-description validator, both of which are more machinery than one sensor warrants. The value function is the right home.

### Extract the logic into an HA-free `temperature.py`

The validation lives in a new `custom_components/perfectdraft/temperature.py` rather than directly in `sensor.py`, and `sensor.py` imports it.

The reason is testability. `sensor.py` imports `homeassistant.components.sensor` at module scope, so any test touching `_get_temperature` needs the full Home Assistant harness — `pytest-homeassistant-custom-component`, a heavyweight install that is not currently provisioned in this checkout. The repository already solved this problem once: `keg_detection.py` exists purely so that the keg-change logic can be exercised by `tests/test_keg_detection.py` under plain `python3 -m unittest`, with the docstring stating the intent outright. Temperature validation is the same kind of pure logic and gets the same treatment.

The module exposes `TEMP_MIN_PLAUSIBLE`, `TEMP_MAX_PLAUSIBLE`, `plausible_temperature(value)` and `beer_temperature(details)`, mirroring how `keg_detection.py` exposes both its constants and its predicate. `_get_temperature` in `sensor.py` becomes a one-line adapter that hands `_get_details(data)` to `beer_temperature`, keeping the value-function table unchanged.

Alternative considered: provision `.venv-test` and write the tests against `sensor.py` directly. Rejected as the primary approach because it makes the new tests unrunnable for anyone without the harness, whereas the split costs one small module and leaves the harness route available for future entity-level tests.

### Coerce defensively

The helper wraps `float()` in `try/except (TypeError, ValueError)` and returns `None` on failure. The current code would raise if the API ever returned a non-numeric temperature, and an exception inside a value function propagates into the entity state update. Cheap insurance, consistent with the tolerant parsing elsewhere in this module.

### Preserve the fallback chain

Order of preference is unchanged: a plausible non-zero `displayedBeerTemperatureInCelsius`, else a plausible `details.temperature`, else `None`. Importantly, an implausible displayed value now *falls through* to the fallback rather than short-circuiting — if the displayed field reads `-128` while `details.temperature` holds something sane, we report the sane one.

## Risks / Trade-offs

- **The bounds reject a legitimate extreme reading** → Bounds are named constants and deliberately wide; a machine reading outside −20…50 °C has bigger problems than a wrong sensor value. Revising them is a one-line change.
- **`-128` is not the only sentinel, and another falls inside the range** → The range check is strictly better than the `-128`-only match the issue proposed, but cannot catch an in-range sentinel. Unknowable without more field data; the one-warning-per-value logging pattern is not added here since a plausible-looking sentinel is indistinguishable from a real reading by definition.
- **Users still see the old bad statistics after upgrading and reopen the issue** → Call it out explicitly in the release notes and in the reply on issue #4.
- **Silent filtering hides a genuinely failing probe** → Accepted. A probe stuck at `-128` indefinitely will show as a permanently `unknown` sensor, which is a clearer signal to the user than a confident `-128 °C`.

## Open Questions

None blocking. Two follow-ups are deliberately deferred and should be filed as separate issues rather than resolved here: the `!= 0` check discarding a real 0 °C reading, and whether `details.temperature` reports the measurement or the setpoint.
