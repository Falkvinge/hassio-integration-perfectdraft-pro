"""Image entity for PerfectDraft keg artwork."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.image import ImageEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator


_IMAGE_CANDIDATE_KEYS = (
    "kegImage",
    "keg_image",
    "imageUrl",
    "image_url",
    "beerImage",
    "beer_image",
    "image",
)


def _get_image_url(data: dict[str, Any]) -> str | None:
    for key in _IMAGE_CANDIDATE_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict):
            inner = val.get("url") or val.get("src")
            if isinstance(inner, str) and inner.startswith("http"):
                return inner

    keg = data.get("keg")
    if isinstance(keg, dict):
        for key in ("image", "imageUrl", "image_url"):
            val = keg.get(key)
            if isinstance(val, str) and val.startswith("http"):
                return val
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft image entity."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PerfectDraftKegImage(coordinator)])


class PerfectDraftKegImage(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ImageEntity
):
    """Displays the current keg's artwork."""

    _attr_has_entity_name = True
    _attr_name = "Keg Image"

    def __init__(
        self, coordinator: PerfectDraftDataUpdateCoordinator
    ) -> None:
        super().__init__(coordinator)
        data = coordinator.data or {}
        machine_id = data.get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_keg_image"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, machine_id)},
            name="PerfectDraft Pro",
            manufacturer="PerfectDraft",
            model="Pro",
        )
        self._current_url: str | None = None

    @property
    def image_url(self) -> str | None:
        data = self.coordinator.data
        if not data:
            return None
        url = _get_image_url(data)
        if url != self._current_url:
            self._current_url = url
            self._attr_image_last_updated = datetime.now()
        return url

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data
        return data is not None and _get_image_url(data) is not None
