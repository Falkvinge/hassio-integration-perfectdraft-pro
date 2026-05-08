"""Number entities for PerfectDraft controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import device_info, setting, update_setting

DEFAULT_MIN_TEMP = 3.0
DEFAULT_MAX_TEMP = 7.0


@dataclass(frozen=True, kw_only=True)
class PerfectDraftNumberDescription(NumberEntityDescription):
    """Description for a PerfectDraft number entity."""

    value_fn: Callable[[dict[str, Any]], float | None]
    update_key: str


def _temperature_min(data: dict[str, Any]) -> float:
    current = data.get("setting") or {}
    return float(current.get("temperatureMin") or DEFAULT_MIN_TEMP)


def _temperature_max(data: dict[str, Any]) -> float:
    current = data.get("setting") or {}
    return float(current.get("temperatureMax") or DEFAULT_MAX_TEMP)


def _target_temperature(data: dict[str, Any]) -> float | None:
    val = (data.get("setting") or {}).get("temperature")
    return float(val) if val is not None else None


def _eco_temperature(data: dict[str, Any]) -> float | None:
    val = (data.get("setting") or {}).get("ecoModeBeerTemperatureSetPoint")
    return float(val) if val is not None else None


NUMBER_DESCRIPTIONS: tuple[PerfectDraftNumberDescription, ...] = (
    PerfectDraftNumberDescription(
        key="target_temperature_control",
        translation_key="target_temperature_control",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        icon="mdi:thermometer-check",
        value_fn=_target_temperature,
        update_key="temperature",
    ),
    PerfectDraftNumberDescription(
        key="eco_temperature_control",
        translation_key="eco_temperature_control",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=1,
        icon="mdi:leaf",
        value_fn=_eco_temperature,
        update_key="ecoModeBeerTemperatureSetPoint",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft number entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PerfectDraftNumber(coordinator, description)
        for description in NUMBER_DESCRIPTIONS
    )


class PerfectDraftNumber(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], NumberEntity
):
    """A PerfectDraft number control."""

    _attr_has_entity_name = True
    entity_description: PerfectDraftNumberDescription

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
        description: PerfectDraftNumberDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_{description.key}"
        self._attr_device_info = device_info(coordinator)

    @property
    def native_min_value(self) -> float:
        return _temperature_min(self.coordinator.data or {})

    @property
    def native_max_value(self) -> float:
        return _temperature_max(self.coordinator.data or {})

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def available(self) -> bool:
        return super().available and setting(self.coordinator).get("id") is not None

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value through the PerfectDraft settings API."""
        value = max(self.native_min_value, min(self.native_max_value, value))
        await update_setting(
            self.coordinator,
            {self.entity_description.update_key: value},
        )
