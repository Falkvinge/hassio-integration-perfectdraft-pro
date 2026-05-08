"""PerfectDraft Pro integration for Home Assistant."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory

from .api import PerfectDraftApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import PerfectDraftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_POLL_INTERVAL = "set_poll_interval_seconds"
ATTR_INTERVAL = "interval"
OBSOLETE_ACTIVE_BEER_DETAIL_KEYS = {
    "beer_brewery",
    "beer_style",
    "beer_country",
    "beer_abv",
    "beer_serving_temperature",
    "beer_sku",
    "beer_url",
}

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INTERVAL): vol.All(
            int, vol.Range(min=MIN_SCAN_INTERVAL)
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PerfectDraft from a config entry."""
    session = async_get_clientsession(hass)
    client = PerfectDraftApiClient(session)

    client.set_tokens(
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    coordinator = PerfectDraftDataUpdateCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_migrate_favorite_beer_entities(hass, entry)
    _async_remove_obsolete_active_beer_detail_entities(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a PerfectDraft config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_SET_POLL_INTERVAL)
    return unload_ok


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Migrate old config entry versions."""
    _LOGGER.debug(
        "Migrating config entry from version %s", config_entry.version
    )
    return True


def _async_migrate_favorite_beer_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Mark existing favourite beer entities as diagnostic/debug entities."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if not entity.entity_id.startswith("sensor."):
            continue
        unique_id = str(entity.unique_id or "")
        entity_id = entity.entity_id
        if "_favorite_beer" not in unique_id and "_favorite_beer" not in entity_id:
            continue
        registry.async_update_entity(
            entity.entity_id,
            entity_category=EntityCategory.DIAGNOSTIC,
        )


def _async_remove_obsolete_active_beer_detail_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove active beer detail entities now exposed as Beer attributes."""
    registry = er.async_get(hass)
    machine_id_prefix = None
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None:
        machine_id = (coordinator.data or {}).get("_machine_id")
        if machine_id is not None:
            machine_id_prefix = f"{machine_id}_"

    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = str(entity.unique_id or "")
        if _is_obsolete_active_beer_detail_unique_id(unique_id, machine_id_prefix):
            registry.async_remove(entity.entity_id)


def _is_obsolete_active_beer_detail_unique_id(
    unique_id: str,
    machine_id_prefix: str | None,
) -> bool:
    """Return whether a unique ID is an obsolete active beer detail sensor."""
    if machine_id_prefix and not unique_id.startswith(machine_id_prefix):
        return False
    return any(
        unique_id.endswith(f"_{key}") for key in OBSOLETE_ACTIVE_BEER_DETAIL_KEYS
    )


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update — adjust coordinator polling interval."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval_from_options()


def _register_services(hass: HomeAssistant) -> None:
    """Register custom services (idempotent — safe to call multiple times)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_POLL_INTERVAL):
        return

    async def handle_set_poll_interval(call: ServiceCall) -> None:
        interval = call.data[ATTR_INTERVAL]
        coordinators: dict = hass.data.get(DOMAIN, {})
        for coordinator in coordinators.values():
            if isinstance(coordinator, PerfectDraftDataUpdateCoordinator):
                coordinator.update_interval = timedelta(seconds=interval)
                _LOGGER.info("Polling interval set to %s seconds via service call", interval)
                await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_POLL_INTERVAL,
        handle_set_poll_interval,
        schema=SERVICE_SCHEMA,
    )
