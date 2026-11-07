"""Unit tests for machine controls (number, select, and api settings methods)."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any
import unittest
from unittest.mock import AsyncMock, MagicMock

_PKG_DIR = Path(__file__).resolve().parent.parent / "custom_components" / "perfectdraft"


def _ensure_ha_stubs() -> None:
    if "homeassistant" in sys.modules:
        return
    ha = types.ModuleType("homeassistant")
    ha_config_entries = types.ModuleType("homeassistant.config_entries")
    ha_config_entries.ConfigEntry = object
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.PERCENTAGE = "%"
    ha_const.UnitOfPressure = types.SimpleNamespace(KPA="kPa")
    ha_const.UnitOfTemperature = types.SimpleNamespace(CELSIUS="°C")
    ha_const.UnitOfTime = types.SimpleNamespace(SECONDS="s", MINUTES="min")
    ha_const.UnitOfVolume = types.SimpleNamespace(LITERS="L")
    ha_core = types.ModuleType("homeassistant.core")
    ha_core.HomeAssistant = object
    ha_core.ServiceCall = object
    ha_core.callback = lambda fn: fn
    ha_exc = types.ModuleType("homeassistant.exceptions")
    ha_exc.ConfigEntryAuthFailed = type("ConfigEntryAuthFailed", (Exception,), {})
    ha_exc.HomeAssistantError = type("HomeAssistantError", (Exception,), {})
    ha_helpers = types.ModuleType("homeassistant.helpers")
    ha_dev_reg = types.ModuleType("homeassistant.helpers.device_registry")
    ha_dev_reg.DeviceInfo = dict
    ha_disp = types.ModuleType("homeassistant.helpers.dispatcher")
    ha_disp.async_dispatcher_connect = lambda *a, **kw: None
    ha_disp.async_dispatcher_send = lambda *a, **kw: None
    ha_ent_plat = types.ModuleType("homeassistant.helpers.entity_platform")
    ha_ent_plat.AddEntitiesCallback = object
    ha_restore = types.ModuleType("homeassistant.helpers.restore_state")
    ha_restore.RestoreEntity = type("RestoreEntity", (), {})
    ha_coord = types.ModuleType("homeassistant.helpers.update_coordinator")

    class _DummyGeneric:
        def __class_getitem__(cls, item):
            return cls

    class _DummyCoordinatorEntity:
        def __init__(self, coordinator=None):
            self.coordinator = coordinator
        def __class_getitem__(cls, item):
            return cls

    ha_coord.DataUpdateCoordinator = _DummyGeneric
    ha_coord.CoordinatorEntity = _DummyCoordinatorEntity
    ha_coord.UpdateFailed = type("UpdateFailed", (Exception,), {})

    ha_comp = types.ModuleType("homeassistant.components")
    ha_sensor = types.ModuleType("homeassistant.components.sensor")
    ha_sensor.SensorDeviceClass = types.SimpleNamespace(
        TEMPERATURE="temperature",
        VOLUME_STORAGE="volume_storage",
        ENUM="enum",
        DURATION="duration",
        PRESSURE="pressure",
    )
    ha_sensor.SensorEntity = type("SensorEntity", (), {})

    @dataclass(frozen=True, kw_only=True)
    class _SensorEntityDescription:
        key: str = ""
        translation_key: str | None = None
        device_class: Any = None
        native_unit_of_measurement: str | None = None
        state_class: Any = None
        icon: str | None = None
        suggested_display_precision: int | None = None
        options: list[str] | None = None
        entity_registry_enabled_default: bool = True

    ha_sensor.SensorEntityDescription = _SensorEntityDescription
    ha_sensor.SensorStateClass = types.SimpleNamespace(
        MEASUREMENT="measurement",
        TOTAL_INCREASING="total_increasing",
    )

    ha_number = types.ModuleType("homeassistant.components.number")
    ha_number.NumberDeviceClass = types.SimpleNamespace(TEMPERATURE="temperature")
    ha_number.NumberMode = types.SimpleNamespace(SLIDER="slider")
    ha_number.NumberEntity = type("NumberEntity", (), {})

    ha_select = types.ModuleType("homeassistant.components.select")
    ha_select.SelectEntity = type("SelectEntity", (), {})

    vol = types.ModuleType("voluptuous")
    vol.Schema = lambda *a, **kw: None
    vol.Required = lambda *a, **kw: None
    vol.All = lambda *a, **kw: None
    vol.Range = lambda *a, **kw: None

    ha_helpers_aiohttp = types.ModuleType("homeassistant.helpers.aiohttp_client")
    ha_helpers_aiohttp.async_get_clientsession = lambda *a: None

    for name, mod in {
        "voluptuous": vol,
        "homeassistant": ha,
        "homeassistant.config_entries": ha_config_entries,
        "homeassistant.const": ha_const,
        "homeassistant.core": ha_core,
        "homeassistant.exceptions": ha_exc,
        "homeassistant.helpers": ha_helpers,
        "homeassistant.helpers.device_registry": ha_dev_reg,
        "homeassistant.helpers.dispatcher": ha_disp,
        "homeassistant.helpers.entity_platform": ha_ent_plat,
        "homeassistant.helpers.restore_state": ha_restore,
        "homeassistant.helpers.update_coordinator": ha_coord,
        "homeassistant.helpers.aiohttp_client": ha_helpers_aiohttp,
        "homeassistant.components": ha_comp,
        "homeassistant.components.sensor": ha_sensor,
        "homeassistant.components.number": ha_number,
        "homeassistant.components.select": ha_select,
    }.items():
        sys.modules[name] = mod


_ensure_ha_stubs()

if "custom_components.perfectdraft" not in sys.modules:
    pkg = types.ModuleType("custom_components.perfectdraft")
    pkg.__path__ = [str(_PKG_DIR)]
    sys.modules["custom_components.perfectdraft"] = pkg


def _load(mod_name: str):
    full = f"custom_components.perfectdraft.{mod_name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, _PKG_DIR / f"{mod_name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[full] = mod
    spec.loader.exec_module(mod)
    return mod


const_mod = _load("const")
_load("exceptions")
_load("temperature")
_load("keg_detection")
_load("api")
sensor_mod = _load("sensor")
coordinator_mod = _load("coordinator")
number_mod = _load("number")
select_mod = _load("select")


class TestTargetTemperatureNumber(unittest.TestCase):
    def test_get_target_temperature_from_setting(self):
        data = {"details": {}, "setting": {"temperature": 5}}
        self.assertEqual(number_mod._get_target_temperature(data), 5.0)

    def test_get_target_temperature_none(self):
        self.assertIsNone(number_mod._get_target_temperature({}))
        self.assertIsNone(number_mod._get_target_temperature(None))

    def test_number_entity_properties(self):
        coordinator = MagicMock()
        coordinator.data = {
            "_machine_id": "test_machine_1",
            "setting": {"temperature": 3, "temperatureMin": 2, "temperatureMax": 6},
        }
        entity = number_mod.PerfectDraftTargetTemperatureNumber(coordinator)
        self.assertEqual(entity.native_value, 3.0)
        self.assertEqual(
            entity.extra_state_attributes,
            {"recommended_min_temperature": 2, "recommended_max_temperature": 6},
        )


class TestTargetTemperatureWrite(unittest.IsolatedAsyncioTestCase):
    async def _set(self, setting: dict[str, Any], value: float) -> dict[str, Any]:
        coordinator = MagicMock()
        coordinator.data = {"_machine_id": "m1", "setting": setting}
        coordinator.async_update_settings = AsyncMock()
        entity = number_mod.PerfectDraftTargetTemperatureNumber(coordinator)
        await entity.async_set_native_value(value)
        return coordinator.async_update_settings.await_args.kwargs

    async def test_standard_sends_temperature_only(self):
        changes = await self._set({"mode": "standard", "ecoModeEnabled": False}, 4)
        self.assertEqual(changes, {"temperature": 4})

    async def test_eco_switches_to_standard(self):
        changes = await self._set({"mode": "eco", "ecoModeEnabled": True}, 4)
        self.assertEqual(
            changes, {"temperature": 4, "mode": "standard", "ecoModeEnabled": False}
        )

    async def test_eco_flag_with_standard_mode_switches_too(self):
        changes = await self._set({"mode": "standard", "ecoModeEnabled": True}, 6)
        self.assertEqual(changes["mode"], "standard")
        self.assertIs(changes["ecoModeEnabled"], False)


class TestModeSelect(unittest.TestCase):
    def test_selectable_options(self):
        self.assertIn("standard", const_mod.SELECTABLE_MODE_OPTIONS)
        self.assertIn("eco", const_mod.SELECTABLE_MODE_OPTIONS)
        # The backend rejects boost on PUT (500 for mode "boost", 400 for
        # boost: true), so it is read-only.
        self.assertNotIn("boost", const_mod.SELECTABLE_MODE_OPTIONS)

    def test_current_option(self):
        coordinator = MagicMock()
        coordinator.data = {"setting": {"mode": "eco"}}
        select = select_mod.PerfectDraftModeSelect(coordinator)
        self.assertEqual(select.current_option, "eco")


class TestKegSelect(unittest.TestCase):
    def test_build_keg_maps(self):
        catalog = {
            100: "Stella Artois",
            101: "Leffe Blonde",
            102: "Stella Artois",
        }
        options, option_to_id, id_to_option = select_mod._build_keg_maps(catalog)
        self.assertIn("Leffe Blonde", options)
        # Disambiguates duplicate names
        self.assertIn("Stella Artois (#100)", options)
        self.assertIn("Stella Artois (#102)", options)
        self.assertEqual(option_to_id["Leffe Blonde"], 101)
        self.assertEqual(id_to_option[101], "Leffe Blonde")


class TestCoordinatorReconcile(unittest.TestCase):
    def test_get_setting_id(self):
        data = {"setting": {"id": 123}}
        self.assertEqual(coordinator_mod.get_setting_id(data), "123")
        data_iri = {"setting": {"@id": "/api/perfectdraft_machine_settings/456"}}
        self.assertEqual(coordinator_mod.get_setting_id(data_iri), "456")
        data_fallback = {"_machine_id": "789"}
        self.assertEqual(coordinator_mod.get_setting_id(data_fallback), "789")

    def test_reconcile_settings_reflects_api_change(self):
        api_setting = {"temperature": 4, "mode": "boost", "updatedAt": "2026-10-06T12:00:00Z"}
        hw_settings = {"temperature": 3, "mode": "standard"}
        merged, updated_at = coordinator_mod.reconcile_settings(
            api_setting, hw_settings, prev_updated_at="2026-10-06T11:00:00Z"
        )
        self.assertEqual(merged["temperature"], 4)
        self.assertEqual(merged["mode"], "boost")
        self.assertEqual(updated_at, "2026-10-06T12:00:00Z")


if __name__ == "__main__":
    unittest.main()
