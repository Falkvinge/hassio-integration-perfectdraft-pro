"""Select entities for PerfectDraft controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MODE_OPTIONS, VOLUME_THRESHOLD_OPTIONS
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import device_info, setting, update_setting


@dataclass(frozen=True, kw_only=True)
class PerfectDraftSelectDescription(SelectEntityDescription):
    """Description for a PerfectDraft select entity."""

    current_fn: Callable[[dict[str, Any]], str | None]
    options_fn: Callable[[dict[str, Any]], list[str]]
    update_fn: Callable[[str], dict[str, Any]]


def _mode(data: dict[str, Any]) -> str | None:
    val = (data.get("setting") or {}).get("mode")
    return str(val) if val is not None else None


def _mode_options(data: dict[str, Any]) -> list[str]:
    return MODE_OPTIONS


def _mode_update(option: str) -> dict[str, Any]:
    return {"mode": option}


def _threshold(data: dict[str, Any]) -> str | None:
    val = (data.get("setting") or {}).get("volumeThreshold")
    return str(val) if val is not None else None


def _threshold_options(data: dict[str, Any]) -> list[str]:
    values = (data.get("setting") or {}).get("volumeThresholdValues")
    if isinstance(values, list) and values:
        return [str(value) for value in values]
    return [str(value) for value in VOLUME_THRESHOLD_OPTIONS]


def _threshold_update(option: str) -> dict[str, Any]:
    return {"volumeThreshold": float(option)}


SELECT_DESCRIPTIONS: tuple[PerfectDraftSelectDescription, ...] = (
    PerfectDraftSelectDescription(
        key="mode_control",
        translation_key="mode_control",
        icon="mdi:tune-variant",
        current_fn=_mode,
        options_fn=_mode_options,
        update_fn=_mode_update,
    ),
    PerfectDraftSelectDescription(
        key="volume_threshold_control",
        translation_key="volume_threshold_control",
        icon="mdi:keg-outline",
        current_fn=_threshold,
        options_fn=_threshold_options,
        update_fn=_threshold_update,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft select entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PerfectDraftSelect(coordinator, description)
        for description in SELECT_DESCRIPTIONS
    )


class PerfectDraftSelect(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SelectEntity
):
    """A PerfectDraft select control."""

    _attr_has_entity_name = True
    entity_description: PerfectDraftSelectDescription

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
        description: PerfectDraftSelectDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_{description.key}"
        self._attr_device_info = device_info(coordinator)

    @property
    def options(self) -> list[str]:
        return self.entity_description.options_fn(self.coordinator.data or {})

    @property
    def current_option(self) -> str | None:
        return self.entity_description.current_fn(self.coordinator.data or {})

    @property
    def available(self) -> bool:
        return super().available and setting(self.coordinator).get("id") is not None

    @property
    def entity_category(self) -> EntityCategory | None:
        if self.entity_description.key == "volume_threshold_control":
            return EntityCategory.CONFIG
        return None

    async def async_select_option(self, option: str) -> None:
        """Select an option through the PerfectDraft settings API."""
        await update_setting(self.coordinator, self.entity_description.update_fn(option))
