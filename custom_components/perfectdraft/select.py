"""Select entities for PerfectDraft."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SELECTABLE_MODE_OPTIONS, keg_changed_signal
from .coordinator import PerfectDraftDataUpdateCoordinator
from .sensor import (
    _KEG_CATALOG,
    _device_info,
    _get_keg_name,
    _get_keg_product_id,
    _get_mode,
)


def _build_keg_maps(catalog: dict[int, str]) -> tuple[list[str], dict[str, int], dict[int, str]]:
    """Build sorted option list and bidirectional mappings between display name and product ID."""
    name_counts: dict[str, int] = {}
    for name in catalog.values():
        name_counts[name] = name_counts.get(name, 0) + 1

    option_to_id: dict[str, int] = {}
    id_to_option: dict[int, str] = {}
    for pid, name in catalog.items():
        label = f"{name} (#{pid})" if name_counts.get(name, 0) > 1 else name
        option_to_id[label] = pid
        id_to_option[pid] = label

    options = sorted(option_to_id.keys(), key=str.casefold)
    return options, option_to_id, id_to_option


_KEG_OPTIONS, _KEG_OPTION_TO_ID, _KEG_ID_TO_OPTION = _build_keg_maps(_KEG_CATALOG)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft select entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PerfectDraftModeSelect(coordinator),
            PerfectDraftKegSelect(coordinator),
        ]
    )


class PerfectDraftModeSelect(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SelectEntity
):
    """Select entity for the PerfectDraft operating mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "mode"
    _attr_icon = "mdi:tune"
    _attr_options = list(SELECTABLE_MODE_OPTIONS)

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{self._machine_id}_mode_select"
        self._attr_device_info = _device_info(coordinator)

    @property
    def current_option(self) -> str | None:
        """Return the current operating mode if it is in the selectable options."""
        mode = _get_mode(self.coordinator.data or {})
        if mode in SELECTABLE_MODE_OPTIONS:
            return mode
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the machine operating mode."""
        normalized = option.strip().lower()
        if normalized not in SELECTABLE_MODE_OPTIONS:
            raise HomeAssistantError(f"Unsupported mode: {option}")
        await self.coordinator.async_update_settings(
            mode=normalized,
            boost=False,
            ecoModeEnabled=(normalized == "eco"),
            ecoModeSchedulerEnabled=False,
        )


class PerfectDraftKegSelect(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], SelectEntity
):
    """Select entity to choose the active keg installed in the machine."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_keg"
    _attr_icon = "mdi:keg"
    _attr_options = _KEG_OPTIONS

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self._machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{self._machine_id}_active_keg_select"
        self._attr_device_info = _device_info(coordinator)

    @property
    def current_option(self) -> str | None:
        """Return the currently active keg option if recognized."""
        data = self.coordinator.data or {}
        pid = _get_keg_product_id(data)
        if pid is not None and pid in _KEG_ID_TO_OPTION:
            return _KEG_ID_TO_OPTION[pid]
        name = _get_keg_name(data)
        if name and name in _KEG_OPTION_TO_ID:
            return name
        return None

    async def async_select_option(self, option: str) -> None:
        """Assign the selected keg to the machine via the PerfectDraft API."""
        product_id = _KEG_OPTION_TO_ID.get(option)
        if product_id is None:
            raise HomeAssistantError(f"Unknown keg selection: {option}")
        await self.coordinator.async_set_active_keg(product_id)
        if self.hass is not None:
            async_dispatcher_send(self.hass, keg_changed_signal(self._machine_id))
