"""Pure temperature extraction logic — no Home Assistant dependencies.

Kept import-free so the validation can be unit-tested standalone,
without a Home Assistant test harness.
"""
from __future__ import annotations

from typing import Any

# Readings outside this closed range are firmware sentinels, not measurements.
# An uninitialised probe reports -128 (0x80 read as a signed 8-bit integer)
# while the refrigeration starts up, and the cloud API relays it verbatim.
TEMP_MIN_PLAUSIBLE = -20.0
TEMP_MAX_PLAUSIBLE = 50.0


def plausible_temperature(value: Any) -> float | None:
    """Return ``value`` as a float when it could be a real reading, else None."""
    if value is None:
        return None
    try:
        temp = float(value)
    except (TypeError, ValueError):
        return None
    if not TEMP_MIN_PLAUSIBLE <= temp <= TEMP_MAX_PLAUSIBLE:
        return None
    return temp


def beer_temperature(details: dict) -> float | None:
    """Pick the beer temperature out of a machine's ``details`` payload.

    Prefers ``displayedBeerTemperatureInCelsius`` and falls back to
    ``temperature``. An implausible or zero displayed value falls through to
    the fallback rather than short-circuiting, so a sane fallback still wins
    over a sentinel. Zero is rejected on the displayed field only, matching a
    firmware that reports 0 before the probe initialises.
    """
    displayed = plausible_temperature(details.get("displayedBeerTemperatureInCelsius"))
    if displayed is not None and displayed != 0:
        return displayed
    return plausible_temperature(details.get("temperature"))
