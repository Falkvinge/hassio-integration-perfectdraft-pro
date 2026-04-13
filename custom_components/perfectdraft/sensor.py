"""Sensor entities for PerfectDraft."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator

KEG_TOTAL_VOLUME = 6.0  # litres
KEG_FRESHNESS_DAYS = 30
KEG_NEW_VOLUME_THRESHOLD = 5.5  # litres — above this + pours==0 means new keg


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
    return round(float(val) * 1000)  # litres -> ml


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

    entities: list[SensorEntity] = [
        PerfectDraftSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(PerfectDraftKegFreshnessSensor(coordinator))

    async_add_entities(entities)


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


class PerfectDraftKegFreshnessSensor(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator],
    RestoreEntity,
    SensorEntity,
):
    """Tracks keg freshness as a 30-day countdown from insertion.

    Detects new keg insertion when numberOfPoursSinceStartup resets to 0
    and kegVolume is near full. Persists the insertion timestamp across
    HA restarts via RestoreEntity.
    """

    _attr_has_entity_name = True
    _attr_translation_key = "keg_freshness"
    _attr_native_unit_of_measurement = "d"
    _attr_icon = "mdi:calendar-clock"

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_keg_freshness"
        self._attr_device_info = _device_info(coordinator)
        self._keg_inserted_at: datetime | None = None
        self._last_pours: int | None = None

    async def async_added_to_hass(self) -> None:
        """Restore keg insertion date from previous session."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.attributes:
            iso = last_state.attributes.get("keg_inserted_at")
            if iso:
                try:
                    self._keg_inserted_at = datetime.fromisoformat(iso)
                except (ValueError, TypeError):
                    pass
            pours = last_state.attributes.get("last_pours")
            if pours is not None:
                self._last_pours = int(pours)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose keg insertion date as an attribute (also used for restore)."""
        return {
            "keg_inserted_at": self._keg_inserted_at.isoformat() if self._keg_inserted_at else None,
            "last_pours": self._last_pours,
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        """Detect new keg insertion on each data update."""
        data = self.coordinator.data
        if not data:
            super()._handle_coordinator_update()
            return

        details = data.get("details") or {}
        pours = details.get("numberOfPoursSinceStartup")
        volume = details.get("kegVolume")

        if pours is not None and volume is not None:
            is_new_keg = (
                pours == 0
                and float(volume) > KEG_NEW_VOLUME_THRESHOLD
                and self._last_pours != 0
            )
            if is_new_keg:
                self._keg_inserted_at = datetime.now(timezone.utc)

            self._last_pours = int(pours)

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> int | None:
        if self._keg_inserted_at is None:
            return None
        elapsed = (datetime.now(timezone.utc) - self._keg_inserted_at).days
        remaining = KEG_FRESHNESS_DAYS - elapsed
        return max(remaining, 0)

    @property
    def available(self) -> bool:
        return super().available and self._keg_inserted_at is not None


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
