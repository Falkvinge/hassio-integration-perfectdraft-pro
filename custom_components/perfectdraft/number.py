"""Number entities for PerfectDraft."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator
from .sensor import _device_info

MIN_TARGET_TEMP = 0.0
MAX_TARGET_TEMP = 12.0


def _is_eco(data: dict[str, Any] | None) -> bool:
    """Return True when the machine setting says Eco mode is on."""
    setting = (data or {}).get("setting") or {}
    return setting.get("mode") == "eco" or setting.get("ecoModeEnabled") is True


def _get_target_temperature(data: dict[str, Any] | None) -> float | None:
    """Return the target temperature from the machine setting."""
    val = ((data or {}).get("setting") or {}).get("temperature")
    return float(val) if val is not None else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft number entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PerfectDraftTargetTemperatureNumber(coordinator)])


class PerfectDraftTargetTemperatureNumber(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], NumberEntity
):
    """Number entity controlling the PerfectDraft target beer temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "target_temperature"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = MIN_TARGET_TEMP
    _attr_native_max_value = MAX_TARGET_TEMP
    _attr_native_step = 1.0
    _attr_icon = "mdi:thermometer-check"

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{self._machine_id}_target_temperature_number"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> float | None:
        """Return the current target temperature."""
        return _get_target_temperature(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the recommended beer temperature bounds reported by the API."""
        setting = (self.coordinator.data or {}).get("setting") or {}
        if not isinstance(setting, dict):
            return None
        return {
            "recommended_min_temperature": setting.get("temperatureMin"),
            "recommended_max_temperature": setting.get("temperatureMax"),
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set a new target temperature on the PerfectDraft machine."""
        if not (MIN_TARGET_TEMP <= value <= MAX_TARGET_TEMP):
            raise HomeAssistantError(
                f"Target temperature {value}°C is outside allowed range ({MIN_TARGET_TEMP}°C - {MAX_TARGET_TEMP}°C)"
            )
        target = int(round(value))
        changes: dict[str, Any] = {"temperature": target}
        if _is_eco(self.coordinator.data):
            # Eco cools to its own setpoint and ignores "temperature", so a new
            # target only takes effect in Standard. The PerfectDraft app does
            # the same: changing the temperature while in Eco leaves Eco.
            changes.update(mode="standard", ecoModeEnabled=False)
        await self.coordinator.async_update_settings(**changes)
