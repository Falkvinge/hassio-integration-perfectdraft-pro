"""Button entities for PerfectDraft."""
from __future__ import annotations

from homeassistant.components import persistent_notification
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import active_product_id, catalogue_attributes, catalogue_value, device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft button entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PerfectDraftOrderAgainButton(coordinator)])


class PerfectDraftOrderAgainButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Create a clickable notification for ordering the active keg again."""

    _attr_has_entity_name = True
    _attr_translation_key = "order_again"
    _attr_icon = "mdi:cart"

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_order_again"
        self._attr_device_info = device_info(coordinator)

    @property
    def available(self) -> bool:
        return super().available and bool(catalogue_value(self._product_id, "url"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return catalogue_attributes(self._product_id)

    @property
    def _product_id(self) -> str | None:
        return active_product_id(self.coordinator)

    async def async_press(self) -> None:
        """Create a Home Assistant notification containing the order URL."""
        product_id = self._product_id
        url = catalogue_value(product_id, "url")
        name = catalogue_value(product_id, "name") or "PerfectDraft keg"
        if not url:
            return

        persistent_notification.async_create(
            self.hass,
            f"[Open the PerfectDraft product page for {name}]({url})",
            title=f"Order {name} again",
            notification_id="perfectdraft_order_again",
        )
