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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .catalogue import lookup_product
from .const import DOMAIN, MAX_FAVORITE_BEER_SENSORS
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import (
    catalogue_attributes,
    catalogue_value,
    device_info,
    favorite_product_ids,
)

KEG_TOTAL_VOLUME = 6.0  # litres
KEG_FRESHNESS_DAYS = 30
KEG_NEW_VOLUME_THRESHOLD = 5.5  # litres — above this + pours==0 means new keg


@dataclass(frozen=True, kw_only=True)
class PerfectDraftSensorDescription(SensorEntityDescription):
    """Extended description with a value extractor."""

    value_fn: Callable[[dict], Any] = lambda d: None


def _get_details(data: dict) -> dict:
    return data.get("details") or {}


def _get_setting(data: dict) -> dict:
    return data.get("setting") or {}


def _get_active_keg(data: dict) -> dict:
    return data.get("_active_keg") or {}


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _get_keg_product_id(data: dict) -> str | None:
    keg = _get_active_keg(data).get("keg")
    if not keg:
        return None
    return str(keg).rsplit("/", 1)[-1]


def _get_keg_inserted_at(data: dict) -> datetime | None:
    return _parse_datetime(_get_active_keg(data).get("insertedAt"))


def _get_keg_age(data: dict) -> int | None:
    inserted_at = _get_keg_inserted_at(data)
    if inserted_at is None:
        return None
    return max((datetime.now(timezone.utc) - inserted_at).days, 0)


def _get_catalogue(data: dict) -> dict[str, Any]:
    return lookup_product(_get_keg_product_id(data))


def _catalogue_value(data: dict, key: str) -> Any:
    value = _get_catalogue(data).get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _get_beer_name(data: dict) -> str | None:
    return _catalogue_value(data, "name")


def _get_favorite_count(data: dict) -> int:
    return len(favorite_product_ids(data))


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
    return _get_setting(data).get("mode")


def _get_keg_volume(data: dict) -> float | None:
    val = _get_details(data).get("kegVolume")
    return round(float(val), 2) if val is not None else None


def _get_keg_type(data: dict) -> str | None:
    return _get_details(data).get("kegType")


def _get_keg_pressure(data: dict) -> float | None:
    val = _get_details(data).get("kegPressure")
    return round(float(val), 1) if val is not None else None


def _get_target_temperature(data: dict) -> float | None:
    val = _get_setting(data).get("temperature")
    return float(val) if val is not None else None


def _get_pressure_setpoint(data: dict) -> float | None:
    val = _get_setting(data).get("pressure")
    return float(val) if val is not None else None


def _get_boost(data: dict) -> str | None:
    val = _get_setting(data).get("boost")
    if val is None:
        return None
    return "On" if val else "Off"


def _get_eco_temperature(data: dict) -> float | None:
    val = _get_setting(data).get("ecoModeBeerTemperatureSetPoint")
    return float(val) if val is not None else None


def _get_volume_threshold(data: dict) -> float | None:
    val = _get_setting(data).get("volumeThreshold")
    return round(float(val), 2) if val is not None else None


def _get_time_to_target(data: dict) -> int | None:
    val = _get_details(data).get("timeToReachTargetTemperature")
    if val is None:
        return None
    return round(float(val) / 1000)


def _get_last_pour_duration(data: dict) -> int | None:
    val = _get_details(data).get("durationOfLastPour")
    return int(val) if val is not None else None


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
    PerfectDraftSensorDescription(
        key="active_keg_product_id",
        translation_key="active_keg_product_id",
        icon="mdi:identifier",
        value_fn=_get_keg_product_id,
    ),
    PerfectDraftSensorDescription(
        key="active_keg_inserted_at",
        translation_key="active_keg_inserted_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:keg",
        value_fn=_get_keg_inserted_at,
    ),
    PerfectDraftSensorDescription(
        key="keg_age",
        translation_key="keg_age",
        native_unit_of_measurement="d",
        icon="mdi:calendar-start",
        value_fn=_get_keg_age,
    ),
    PerfectDraftSensorDescription(
        key="beer_name",
        translation_key="beer_name",
        icon="mdi:beer",
        value_fn=_get_beer_name,
    ),
    PerfectDraftSensorDescription(
        key="favorite_beers",
        translation_key="favorite_beers",
        icon="mdi:star",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_get_favorite_count,
    ),
    PerfectDraftSensorDescription(
        key="keg_volume",
        translation_key="keg_volume",
        native_unit_of_measurement="L",
        icon="mdi:keg",
        suggested_display_precision=2,
        value_fn=_get_keg_volume,
    ),
    PerfectDraftSensorDescription(
        key="keg_type",
        translation_key="keg_type",
        icon="mdi:keg",
        entity_registry_enabled_default=False,
        value_fn=_get_keg_type,
    ),
    PerfectDraftSensorDescription(
        key="keg_pressure",
        translation_key="keg_pressure",
        native_unit_of_measurement="mbar",
        icon="mdi:gauge",
        suggested_display_precision=0,
        value_fn=_get_keg_pressure,
    ),
    PerfectDraftSensorDescription(
        key="target_temperature",
        translation_key="target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer-check",
        value_fn=_get_target_temperature,
    ),
    PerfectDraftSensorDescription(
        key="pressure_setpoint",
        translation_key="pressure_setpoint",
        native_unit_of_measurement="mbar",
        icon="mdi:gauge",
        entity_registry_enabled_default=False,
        value_fn=_get_pressure_setpoint,
    ),
    PerfectDraftSensorDescription(
        key="boost",
        translation_key="boost",
        icon="mdi:rocket-launch",
        entity_registry_enabled_default=False,
        value_fn=_get_boost,
    ),
    PerfectDraftSensorDescription(
        key="eco_temperature",
        translation_key="eco_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:leaf",
        entity_registry_enabled_default=False,
        value_fn=_get_eco_temperature,
    ),
    PerfectDraftSensorDescription(
        key="volume_threshold",
        translation_key="volume_threshold",
        native_unit_of_measurement="L",
        icon="mdi:keg-outline",
        entity_registry_enabled_default=False,
        value_fn=_get_volume_threshold,
    ),
    PerfectDraftSensorDescription(
        key="time_to_target_temperature",
        translation_key="time_to_target_temperature",
        native_unit_of_measurement="s",
        icon="mdi:timer-sand",
        entity_registry_enabled_default=False,
        value_fn=_get_time_to_target,
    ),
    PerfectDraftSensorDescription(
        key="last_pour_duration",
        translation_key="last_pour_duration",
        native_unit_of_measurement="ms",
        icon="mdi:timer-outline",
        entity_registry_enabled_default=False,
        value_fn=_get_last_pour_duration,
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
    entities.extend(
        PerfectDraftFavoriteBeerSensor(coordinator, index)
        for index in range(MAX_FAVORITE_BEER_SENSORS)
    )
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
        self._attr_device_info = device_info(coordinator)

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key == "beer_name":
            return catalogue_attributes(_get_keg_product_id(self.coordinator.data or {}))
        if self.entity_description.key == "favorite_beers":
            favorites = favorite_product_ids(self.coordinator.data or {})
            return {
                "favorites": [
                    catalogue_attributes(product_id)
                    for product_id in favorites
                ],
            }
        return None


class PerfectDraftFavoriteBeerSensor(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SensorEntity
):
    """A favourite beer sensor backed by /api/me customerProductRatings."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:star"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
        index: int,
    ) -> None:
        super().__init__(coordinator)
        self._index = index
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_favorite_beer_{index + 1}"
        self._attr_name = f"Favorite Beer {index + 1}"
        self._attr_device_info = device_info(coordinator)

    @property
    def native_value(self) -> str | None:
        favorites = favorite_product_ids(self.coordinator.data or {})
        if self._index >= len(favorites):
            return None
        product_id = favorites[self._index]
        return catalogue_value(product_id, "name") or product_id

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._index < len(favorite_product_ids(self.coordinator.data or {}))
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        favorites = favorite_product_ids(self.coordinator.data or {})
        if self._index >= len(favorites):
            return {}
        return catalogue_attributes(favorites[self._index])


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
        self._attr_device_info = device_info(coordinator)
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
        active_keg = _get_active_keg(self.coordinator.data or {})
        server_inserted_at = active_keg.get("insertedAt")
        product_id = _get_keg_product_id(self.coordinator.data or {})
        return {
            "keg_inserted_at": self._keg_inserted_at.isoformat() if self._keg_inserted_at else server_inserted_at,
            "active_keg_product_id": product_id,
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
        active_inserted_at = _get_keg_inserted_at(data)

        if active_inserted_at is not None:
            self._keg_inserted_at = active_inserted_at

        if pours is not None and volume is not None:
            is_new_keg = (
                pours == 0
                and float(volume) > KEG_NEW_VOLUME_THRESHOLD
                and self._last_pours != 0
                and active_inserted_at is None
            )
            if is_new_keg:
                self._keg_inserted_at = datetime.now(timezone.utc)

            self._last_pours = int(pours)

        super()._handle_coordinator_update()

    @property
    def native_value(self) -> int | None:
        inserted_at = self._keg_inserted_at or _get_keg_inserted_at(
            self.coordinator.data or {}
        )
        if inserted_at is None:
            return None
        elapsed = (datetime.now(timezone.utc) - inserted_at).days
        remaining = KEG_FRESHNESS_DAYS - elapsed
        return max(remaining, 0)

    @property
    def available(self) -> bool:
        return super().available and (
            self._keg_inserted_at is not None
            or _get_keg_inserted_at(self.coordinator.data or {}) is not None
        )
