"""Fixtures for the Home Assistant test harness.

Only the pytest suite uses this. ``test_keg_detection.py`` imports the
Home-Assistant-free ``keg_detection`` module and still runs standalone under
``python3 -m unittest discover -s tests``.
"""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make custom_components/perfectdraft loadable in every test."""
    yield
