"""Switch entities for PerfectDraft controls."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import device_info, setting, update_setting


@dataclass(frozen=True, kw_only=True)
class PerfectDraftSwitchDescription(SwitchEntityDescription):
    """Description for a PerfectDraft switch entity."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    available_fn: Callable[[dict[str, Any]], bool]
    turn_on_update: dict[str, Any]
    turn_off_update: dict[str, Any]


def _mode_is_eco(data: dict[str, Any]) -> bool | None:
    mode = (data.get("setting") or {}).get("mode")
    return mode == "eco" if mode is not None else None


def _setting_has(data: dict[str, Any], key: str) -> bool:
    return key in (data.get("setting") or {})


SWITCH_DESCRIPTIONS: tuple[PerfectDraftSwitchDescription, ...] = (
    PerfectDraftSwitchDescription(
        key="eco_mode_control",
        translation_key="eco_mode_control",
        icon="mdi:leaf",
        value_fn=_mode_is_eco,
        available_fn=lambda data: _setting_has(data, "mode"),
        turn_on_update={"mode": "eco"},
        turn_off_update={"mode": "standard"},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft switch entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        PerfectDraftSwitch(coordinator, description)
        for description in SWITCH_DESCRIPTIONS
    )


class PerfectDraftSwitch(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SwitchEntity
):
    """A PerfectDraft switch control."""

    _attr_has_entity_name = True
    entity_description: PerfectDraftSwitchDescription

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
        description: PerfectDraftSwitchDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_{description.key}"
        self._attr_device_info = device_info(coordinator)

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def available(self) -> bool:
        current_setting = setting(self.coordinator)
        return (
            super().available
            and current_setting.get("id") is not None
            and self.entity_description.available_fn(self.coordinator.data or {})
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch through the PerfectDraft settings API."""
        await update_setting(self.coordinator, self.entity_description.turn_on_update)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch through the PerfectDraft settings API."""
        await update_setting(self.coordinator, self.entity_description.turn_off_update)
