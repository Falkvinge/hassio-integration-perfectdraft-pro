"""PerfectDraft Pro integration for Home Assistant."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
