"""Unit tests for the pure temperature extraction logic.

Runs with the stdlib only (no Home Assistant): the logic under test lives
in ``temperature.py`` which has no Home Assistant imports.
"""
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "custom_components", "perfectdraft"),
)

from temperature import (  # noqa: E402
    TEMP_MAX_PLAUSIBLE,
    TEMP_MIN_PLAUSIBLE,
    beer_temperature,
)

# The sentinel an uninitialised probe reports: 0x80 as a signed 8-bit integer.
SENTINEL = -128


class TestBeerTemperature(unittest.TestCase):
    def test_normal_reading_from_displayed_field(self):
        self.assertEqual(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": 3, "temperature": 3}
            ),
            3.0,
        )

    # --- The reported bug: -128 before the probe initialises ---
    def test_sentinel_with_no_usable_fallback(self):
        self.assertIsNone(
            beer_temperature({"displayedBeerTemperatureInCelsius": SENTINEL})
        )

    def test_sentinel_falls_through_to_plausible_fallback(self):
        self.assertEqual(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": SENTINEL, "temperature": 4}
            ),
            4.0,
        )

    def test_sentinel_in_both_fields(self):
        self.assertIsNone(
            beer_temperature(
                {
                    "displayedBeerTemperatureInCelsius": SENTINEL,
                    "temperature": SENTINEL,
                }
            )
        )

    def test_sentinel_in_fallback_field_only(self):
        self.assertIsNone(beer_temperature({"temperature": SENTINEL}))

    # --- Pre-existing behaviour that must not regress ---
    def test_zero_on_displayed_field_falls_through(self):
        self.assertEqual(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": 0, "temperature": 5}
            ),
            5.0,
        )

    def test_fallback_used_when_displayed_absent(self):
        self.assertEqual(beer_temperature({"temperature": 6}), 6.0)

    def test_no_fields_present(self):
        self.assertIsNone(beer_temperature({}))

    def test_both_fields_null(self):
        self.assertIsNone(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": None, "temperature": None}
            )
        )

    # --- Defensive coercion ---
    def test_non_numeric_value_does_not_raise(self):
        self.assertIsNone(
            beer_temperature({"displayedBeerTemperatureInCelsius": "n/a"})
        )

    def test_numeric_string_is_accepted(self):
        self.assertEqual(
            beer_temperature({"displayedBeerTemperatureInCelsius": "3.5"}), 3.5
        )

    # --- Range boundaries are inclusive ---
    def test_lower_bound_accepted(self):
        self.assertEqual(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": TEMP_MIN_PLAUSIBLE}
            ),
            TEMP_MIN_PLAUSIBLE,
        )

    def test_upper_bound_accepted(self):
        self.assertEqual(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": TEMP_MAX_PLAUSIBLE}
            ),
            TEMP_MAX_PLAUSIBLE,
        )

    def test_just_below_lower_bound_rejected(self):
        self.assertIsNone(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": TEMP_MIN_PLAUSIBLE - 0.1}
            )
        )

    def test_just_above_upper_bound_rejected(self):
        self.assertIsNone(
            beer_temperature(
                {"displayedBeerTemperatureInCelsius": TEMP_MAX_PLAUSIBLE + 0.1}
            )
        )


if __name__ == "__main__":
    unittest.main()
