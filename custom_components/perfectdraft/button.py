"""Button entities for PerfectDraft."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator
from .entity import (
    active_product_id,
    catalogue_attributes,
    device_info,
    favorite_product_ids,
    ideal_temperature,
    setting,
    update_setting,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PerfectDraft button entities."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            PerfectDraftApplyIdealTemperatureButton(coordinator),
            PerfectDraftAddCurrentBeerFavoriteButton(coordinator),
            PerfectDraftRefreshMetadataButton(coordinator),
            PerfectDraftUpdateFavoritesButton(coordinator),
            PerfectDraftUpdateAvailableBeersButton(coordinator),
        ]
    )


class PerfectDraftApplyIdealTemperatureButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Set the machine target temperature to the active beer's ideal temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "apply_ideal_temperature"
    _attr_icon = "mdi:thermometer-check"

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_apply_ideal_temperature"
        self._attr_device_info = device_info(coordinator)

    @property
    def _product_id(self) -> str | None:
        return active_product_id(self.coordinator)

    @property
    def _ideal_temperature(self) -> float | None:
        return ideal_temperature(self._product_id, self.coordinator.data or {})

    @property
    def available(self) -> bool:
        return (
            super().available
            and self._ideal_temperature is not None
            and setting(self.coordinator).get("id") is not None
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs = catalogue_attributes(self._product_id, self.coordinator.data or {})
        attrs["target_temperature"] = self._target_temperature
        return attrs

    @property
    def _target_temperature(self) -> float | None:
        ideal = self._ideal_temperature
        if ideal is None:
            return None
        current = setting(self.coordinator)
        min_temp = float(current.get("temperatureMin") or 3)
        max_temp = float(current.get("temperatureMax") or 7)
        return max(min_temp, min(max_temp, ideal))

    async def async_press(self) -> None:
        """Apply the active beer's ideal temperature to the machine."""
        target = self._target_temperature
        if target is None:
            return
        await update_setting(self.coordinator, {"temperature": target})


class PerfectDraftAddCurrentBeerFavoriteButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Add the active beer to the PerfectDraft favourite list."""

    _attr_has_entity_name = True
    _attr_translation_key = "add_current_beer_favorite"
    _attr_icon = "mdi:heart-plus"

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_add_current_beer_favorite"
        self._attr_device_info = device_info(coordinator)

    @property
    def _product_id(self) -> str | None:
        return active_product_id(self.coordinator)

    @property
    def available(self) -> bool:
        product_id = self._product_id
        return (
            super().available
            and product_id is not None
            and product_id not in favorite_product_ids(self.coordinator.data or {})
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        product_id = self._product_id
        attrs = catalogue_attributes(product_id, data)
        attrs["already_favorite"] = (
            product_id is not None and product_id in favorite_product_ids(data)
        )
        return attrs

    async def async_press(self) -> None:
        """Add the active beer to account favourites through the API."""
        product_id = self._product_id
        profile = (self.coordinator.data or {}).get("_profile") or {}
        if product_id is None:
            raise HomeAssistantError("No active PerfectDraft keg product ID is available")
        await self.coordinator.client.set_product_favourite(profile, product_id)
        await self.coordinator.async_request_refresh()


def _push_beer_data_update(coordinator: PerfectDraftDataUpdateCoordinator) -> None:
    """Update entities from the latest persisted beer-data snapshot."""
    data = dict(coordinator.data or {})
    data["_beer_data"] = coordinator.beer_data.snapshot()
    coordinator.async_set_updated_data(data)


class PerfectDraftRefreshMetadataButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Refresh cached metadata for the active beer or one favourite."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh_beer_metadata"
    _attr_icon = "mdi:database-refresh"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_refresh_beer_metadata"
        self._attr_device_info = device_info(coordinator)

    @property
    def available(self) -> bool:
        return super().available and (
            active_product_id(self.coordinator) is not None
            or bool(favorite_product_ids(self.coordinator.data or {}))
        )

    async def async_press(self) -> None:
        """Refresh one metadata page, respecting the website fetch gap."""
        product_id = active_product_id(self.coordinator)
        attrs = catalogue_attributes(product_id, self.coordinator.data or {})
        current_item = attrs.get("name") or product_id or "PerfectDraft beer"
        await self.coordinator.beer_data.async_set_job_status(
            "running",
            job_type="metadata_refresh",
            current_item=current_item,
            processed=0,
            total=1,
        )
        _push_beer_data_update(self.coordinator)
        try:
            refreshed = await self.coordinator.beer_data.async_refresh_active_and_favorite_metadata(
                favorite_product_ids(self.coordinator.data or {}),
                product_id,
            )
        except Exception as err:
            await self.coordinator.beer_data.async_set_job_status(
                "failed",
                job_type="metadata_refresh",
                current_item=current_item,
                processed=0,
                total=1,
                last_error=str(err),
            )
            _push_beer_data_update(self.coordinator)
            raise

        if refreshed:
            await self.coordinator.beer_data.async_set_job_status(
                "completed",
                job_type="metadata_refresh",
                current_item=current_item,
                processed=1,
                total=1,
            )
        else:
            await self.coordinator.beer_data.async_set_job_status(
                "skipped",
                job_type="metadata_refresh",
                current_item=current_item,
                processed=0,
                total=1,
                last_error="No product was due or the 60 second website fetch gap has not elapsed.",
            )
        _push_beer_data_update(self.coordinator)


class PerfectDraftUpdateFavoritesButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Refresh account favourites from the PerfectDraft API."""

    _attr_has_entity_name = True
    _attr_translation_key = "update_favorites"
    _attr_icon = "mdi:star-sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_update_favorites"
        self._attr_device_info = device_info(coordinator)

    async def async_press(self) -> None:
        """Refresh coordinator data so favourite beer sensors update now."""
        await self.coordinator.beer_data.async_set_job_status(
            "running",
            job_type="favorites_refresh",
            current_item="PerfectDraft account favorites",
            processed=0,
            total=1,
        )
        _push_beer_data_update(self.coordinator)
        try:
            await self.coordinator.async_request_refresh()
        except Exception as err:
            await self.coordinator.beer_data.async_set_job_status(
                "failed",
                job_type="favorites_refresh",
                current_item="PerfectDraft account favorites",
                processed=0,
                total=1,
                last_error=str(err),
            )
            _push_beer_data_update(self.coordinator)
            raise

        await self.coordinator.beer_data.async_set_job_status(
            "completed",
            job_type="favorites_refresh",
            current_item="PerfectDraft account favorites",
            processed=1,
            total=1,
        )
        _push_beer_data_update(self.coordinator)


class PerfectDraftUpdateAvailableBeersButton(
    CoordinatorEntity[PerfectDraftDataUpdateCoordinator], ButtonEntity
):
    """Discover beers from the curated keg list."""

    _attr_has_entity_name = True
    _attr_translation_key = "update_available_beers"
    _attr_icon = "mdi:keg"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: PerfectDraftDataUpdateCoordinator,
    ) -> None:
        super().__init__(coordinator)
        machine_id = (coordinator.data or {}).get("_machine_id", "unknown")
        self._attr_unique_id = f"{machine_id}_update_available_beers"
        self._attr_device_info = device_info(coordinator)

    async def async_press(self) -> None:
        """Refresh the beer count/list from the curated range page."""
        await self.coordinator.beer_data.async_set_job_status(
            "running",
            job_type="available_beers",
            current_item="PerfectDraft Kegs",
            processed=0,
            total=1,
        )
        _push_beer_data_update(self.coordinator)
        try:
            refreshed = await self.coordinator.beer_data.async_update_available_beers(
                force=True,
            )
        except Exception as err:
            await self.coordinator.beer_data.async_set_job_status(
                "failed",
                job_type="available_beers",
                current_item="PerfectDraft Kegs",
                processed=0,
                total=1,
                last_error=str(err),
            )
            _push_beer_data_update(self.coordinator)
            raise

        await self.coordinator.beer_data.async_set_job_status(
            "completed" if refreshed else "skipped",
            job_type="available_beers",
            current_item="PerfectDraft Kegs",
            processed=1 if refreshed else 0,
            total=1,
            last_error=None if refreshed else "Available beers refresh was skipped.",
        )
        _push_beer_data_update(self.coordinator)
