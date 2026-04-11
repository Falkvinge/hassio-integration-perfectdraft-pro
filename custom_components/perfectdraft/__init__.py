"""PerfectDraft Pro integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PerfectDraftApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import PerfectDraftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PerfectDraft from a config entry."""
    session = async_get_clientsession(hass)
    client = PerfectDraftApiClient(session)

    client.set_tokens(
        access_token=entry.data[CONF_ACCESS_TOKEN],
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    coordinator = PerfectDraftDataUpdateCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a PerfectDraft config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
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
