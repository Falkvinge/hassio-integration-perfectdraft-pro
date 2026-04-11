"""Sensor entities for PerfectDraft."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class PerfectDraftSensorDescription(SensorEntityDescription):
    """Extended description with a value extractor."""

    value_fn: Any = None  # Callable[[dict], Any]


def _get_temperature(data: dict) -> float | None:
    for key in ("temperature", "temp", "currentTemperature"):
        val = data.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None


def _get_percent_remaining(data: dict) -> float | None:
    for key in (
        "beerRemainingPercent",
        "beerRemaining",
        "remaining",
        "volumePercent",
        "volume_percent",
        "percentRemaining",
    ):
        val = data.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    # Fallback: if there's a raw volume out of 6000ml, convert to percent
    for vol_key in ("volume", "beerVolume", "volumeRemaining"):
        vol = data.get(vol_key)
        if vol is not None:
            try:
                return round(float(vol) / 6000.0 * 100, 1)
            except (TypeError, ValueError, ZeroDivisionError):
                pass
    return None


def _get_days_to_expiry(data: dict) -> int | None:
    for key in (
        "daysToExpiry",
        "days_to_expiry",
        "freshnessDays",
        "expiryDays",
        "daysRemaining",
        "freshness",
    ):
        val = data.get(key)
        if val is not None:
            try:
                return int(val)
            except (TypeError, ValueError):
                pass
    return None


def _get_keg_name(data: dict) -> str | None:
    for key in ("kegName", "keg_name", "beerName", "beer_name", "name", "keg"):
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
        if isinstance(val, dict):
            inner = val.get("name") or val.get("brand") or val.get("title")
            if inner:
                return str(inner)
    return None


SENSOR_DESCRIPTIONS: tuple[PerfectDraftSensorDescription, ...] = (
    PerfectDraftSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_get_temperature,
    ),
    PerfectDraftSensorDescription(
        key="percent_remaining",
        translation_key="percent_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:keg",
        value_fn=_get_percent_remaining,
    ),
    PerfectDraftSensorDescription(
        key="days_to_expiry",
        translation_key="days_to_expiry",
        native_unit_of_measurement=UnitOfTime.DAYS,
        icon="mdi:calendar-clock",
        value_fn=_get_days_to_expiry,
    ),
    PerfectDraftSensorDescription(
        key="keg_name",
        translation_key="keg_name",
        icon="mdi:beer",
        value_fn=_get_keg_name,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft sensor entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        PerfectDraftSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PerfectDraftSensor(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SensorEntity
):
    """A PerfectDraft sensor backed by the shared coordinator."""

    _attr_has_entity_name = True
    entity_description: PerfectDraftSensorDescription

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
        description: PerfectDraftSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_{description.key}"
        self._attr_device_info = _device_info(coordinator)

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        return self.native_value is not None


def _device_info(
    coordinator: PerfectDraftDataUpdateCoordinator,
) -> DeviceInfo:
    data = coordinator.data or {}
    machine_id = data.get("_machine_id", "unknown")
    return DeviceInfo(
        identifiers={(DOMAIN, machine_id)},
        name="PerfectDraft Pro",
        manufacturer="PerfectDraft",
        model="Pro",
    )
