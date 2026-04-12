"""Sensor entities for PerfectDraft."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator

KEG_TOTAL_VOLUME = 6.0  # litres


@dataclass(frozen=True, kw_only=True)
class PerfectDraftSensorDescription(SensorEntityDescription):
    """Extended description with a value extractor."""

    value_fn: Callable[[dict], Any] = lambda d: None


def _get_details(data: dict) -> dict:
    return data.get("details") or {}


def _get_temperature(data: dict) -> float | None:
    val = _get_details(data).get("displayedBeerTemperatureInCelsius")
    if val is not None and val != 0:
        return float(val)
    val = _get_details(data).get("temperature")
    return float(val) if val is not None else None


def _get_volume_remaining(data: dict) -> float | None:
    vol = _get_details(data).get("kegVolume")
    if vol is None:
        return None
    return round(float(vol) / KEG_TOTAL_VOLUME * 100, 1)


def _get_connection_state(data: dict) -> str | None:
    state = _get_details(data).get("connectedState")
    if state is None:
        return None
    return "Connected" if state else "Disconnected"


def _get_door_state(data: dict) -> str | None:
    closed = _get_details(data).get("doorClosed")
    if closed is None:
        return None
    return "Closed" if closed else "Open"


def _get_pours(data: dict) -> int | None:
    val = _get_details(data).get("numberOfPoursSinceStartup")
    return int(val) if val is not None else None


def _get_last_pour_volume(data: dict) -> float | None:
    val = _get_details(data).get("volumeOfLastPour")
    if val is None or val == 0:
        return None
    return round(float(val) * 1000)  # litres → ml


def _get_firmware(data: dict) -> str | None:
    return _get_details(data).get("firmwareVersion")


def _get_mode(data: dict) -> str | None:
    setting = data.get("setting") or {}
    return setting.get("mode")


SENSOR_DESCRIPTIONS: tuple[PerfectDraftSensorDescription, ...] = (
    PerfectDraftSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=_get_temperature,
    ),
    PerfectDraftSensorDescription(
        key="keg_remaining",
        translation_key="keg_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:keg",
        suggested_display_precision=0,
        value_fn=_get_volume_remaining,
    ),
    PerfectDraftSensorDescription(
        key="connection",
        translation_key="connection",
        icon="mdi:wifi",
        value_fn=_get_connection_state,
    ),
    PerfectDraftSensorDescription(
        key="door",
        translation_key="door",
        icon="mdi:door",
        value_fn=_get_door_state,
    ),
    PerfectDraftSensorDescription(
        key="pours",
        translation_key="pours",
        icon="mdi:beer",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_get_pours,
    ),
    PerfectDraftSensorDescription(
        key="last_pour",
        translation_key="last_pour",
        native_unit_of_measurement="mL",
        icon="mdi:glass-mug-variant",
        value_fn=_get_last_pour_volume,
    ),
    PerfectDraftSensorDescription(
        key="firmware",
        translation_key="firmware",
        icon="mdi:chip",
        entity_registry_enabled_default=False,
        value_fn=_get_firmware,
    ),
    PerfectDraftSensorDescription(
        key="mode",
        translation_key="mode",
        icon="mdi:thermostat",
        value_fn=_get_mode,
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


def _device_info(
    coordinator: PerfectDraftDataUpdateCoordinator,
) -> DeviceInfo:
    data = coordinator.data or {}
    machine_id = data.get("_machine_id", "unknown")
    details = data.get("details") or {}
    return DeviceInfo(
        identifiers={(DOMAIN, str(machine_id))},
        name="PerfectDraft Pro",
        manufacturer="PerfectDraft",
        model="Pro",
        sw_version=details.get("firmwareVersion"),
        serial_number=details.get("serialNumber"),
    )
