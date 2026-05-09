"""PerfectDraft Pro integration for Home Assistant."""
from __future__ import annotations

from datetime import timedelta
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import EntityCategory

from .api import PerfectDraftApiClient
from .beer_data import PerfectDraftBeerData
from .const import (
    CONF_ACCESS_TOKEN,
    DATA_BEER_DATA,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import PerfectDraftDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_SET_POLL_INTERVAL = "set_poll_interval_seconds"
SERVICE_SET_IDEAL_TEMPERATURE = "set_ideal_temperature"
SERVICE_REFRESH_SHOP_DATA = "refresh_shop_data"
SERVICE_SET_LOCAL_BEER = "set_local_beer"
ATTR_INTERVAL = "interval"
ATTR_PRODUCT_ID = "product_id"
ATTR_TEMPERATURE = "temperature"
ATTR_NAME = "name"
ATTR_PRODUCT_NAME = "product_name"
ATTR_URL = "url"
ATTR_SKU = "sku"
ATTR_BREWERY = "brewery"
ATTR_STYLE = "style"
ATTR_COUNTRY = "country"
ATTR_ABV = "abv"
ATTR_SIZE = "size"
OBSOLETE_ACTIVE_BEER_DETAIL_KEYS = {
    "beer_brewery",
    "beer_style",
    "beer_country",
    "beer_abv",
    "beer_serving_temperature",
    "beer_sku",
    "beer_url",
}
CONFIG_ENTITY_UNIQUE_ID_SUFFIXES = {
    "_target_temperature_control",
    "_eco_temperature_control",
    "_ideal_temperature_control",
    "_volume_threshold_control",
}
DIAGNOSTIC_ENTITY_UNIQUE_ID_SUFFIXES = {
    "_refresh_beer_metadata",
    "_update_available_beers",
}
NORMAL_ENTITY_UNIQUE_ID_SUFFIXES = {
    "_target_temperature",
    "_eco_temperature",
    "_volume_threshold",
}

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_INTERVAL): vol.All(
            int, vol.Range(min=MIN_SCAN_INTERVAL)
        ),
    }
)

SET_IDEAL_TEMPERATURE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PRODUCT_ID): str,
        vol.Required(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=20)
        ),
    }
)

SET_LOCAL_BEER_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_PRODUCT_ID): str,
        vol.Required(ATTR_NAME): str,
        vol.Optional(ATTR_PRODUCT_NAME): str,
        vol.Optional(ATTR_URL): str,
        vol.Optional(ATTR_SKU): str,
        vol.Optional(ATTR_BREWERY): str,
        vol.Optional(ATTR_STYLE): str,
        vol.Optional(ATTR_COUNTRY): str,
        vol.Optional(ATTR_ABV): str,
        vol.Optional(ATTR_SIZE): str,
        vol.Optional(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=20)
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PerfectDraft from a config entry."""
    session = async_get_clientsession(hass)
    client = PerfectDraftApiClient(session)
    domain_data = hass.data.setdefault(DOMAIN, {})
    beer_data = domain_data.get(DATA_BEER_DATA)
    if beer_data is None:
        beer_data = PerfectDraftBeerData(hass, session)
        await beer_data.async_load()
        domain_data[DATA_BEER_DATA] = beer_data

    client.set_tokens(
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
    )

    coordinator = PerfectDraftDataUpdateCoordinator(hass, client, entry, beer_data)
    await coordinator.async_config_entry_first_refresh()

    domain_data[entry.entry_id] = coordinator

    _async_migrate_favorite_beer_entities(hass, entry)
    _async_migrate_entity_categories(hass, entry)
    _async_remove_obsolete_active_beer_detail_entities(hass, entry)
    _async_remove_obsolete_button_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_migrate_entity_categories(hass, entry)
    _async_remove_obsolete_button_entities(hass, entry)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a PerfectDraft config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    coordinators = [
        item
        for key, item in hass.data.get(DOMAIN, {}).items()
        if key != DATA_BEER_DATA
    ]
    if not coordinators:
        hass.services.async_remove(DOMAIN, SERVICE_SET_POLL_INTERVAL)
        hass.services.async_remove(DOMAIN, SERVICE_SET_IDEAL_TEMPERATURE)
        hass.services.async_remove(DOMAIN, SERVICE_REFRESH_SHOP_DATA)
        hass.services.async_remove(DOMAIN, SERVICE_SET_LOCAL_BEER)
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


def _async_remove_obsolete_button_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Remove button entities intentionally retired from the integration."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = str(entity.unique_id or "")
        if entity.entity_id.startswith("button.") and (
            unique_id.endswith("_order_again") or entity.entity_id.endswith("_order_again")
        ):
            registry.async_remove(entity.entity_id)


def _async_migrate_entity_categories(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Move existing entities into their intended HA registry categories."""
    registry = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        unique_id = str(entity.unique_id or "")
        if any(
            unique_id.endswith(suffix)
            for suffix in CONFIG_ENTITY_UNIQUE_ID_SUFFIXES
        ):
            registry.async_update_entity(
                entity.entity_id,
                entity_category=EntityCategory.CONFIG,
            )
        elif any(
            unique_id.endswith(suffix)
            for suffix in DIAGNOSTIC_ENTITY_UNIQUE_ID_SUFFIXES
        ):
            registry.async_update_entity(
                entity.entity_id,
                entity_category=EntityCategory.DIAGNOSTIC,
            )
        elif any(
            unique_id.endswith(suffix)
            for suffix in NORMAL_ENTITY_UNIQUE_ID_SUFFIXES
        ):
            registry.async_update_entity(
                entity.entity_id,
                entity_category=None,
            )


async def _async_options_updated(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update — adjust coordinator polling interval."""
    coordinator: PerfectDraftDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    coordinator.update_interval_from_options()


def _register_services(hass: HomeAssistant) -> None:
    """Register custom services (idempotent — safe to call multiple times)."""
    async def handle_set_poll_interval(call: ServiceCall) -> None:
        interval = call.data[ATTR_INTERVAL]
        coordinators: dict = hass.data.get(DOMAIN, {})
        for coordinator in coordinators.values():
            if isinstance(coordinator, PerfectDraftDataUpdateCoordinator):
                coordinator.update_interval = timedelta(seconds=interval)
                _LOGGER.info(
                    "Polling interval set to %s seconds via service call",
                    interval,
                )
                await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_SET_POLL_INTERVAL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_POLL_INTERVAL,
            handle_set_poll_interval,
            schema=SERVICE_SCHEMA,
        )

    async def handle_set_ideal_temperature(call: ServiceCall) -> None:
        temperature = call.data[ATTR_TEMPERATURE]
        product_id = call.data.get(ATTR_PRODUCT_ID)
        coordinators = [
            item
            for key, item in hass.data.get(DOMAIN, {}).items()
            if key != DATA_BEER_DATA
            and isinstance(item, PerfectDraftDataUpdateCoordinator)
        ]

        if product_id is None:
            for coordinator in coordinators:
                active = (coordinator.data or {}).get("_active_keg") or {}
                keg = active.get("keg")
                if keg:
                    product_id = str(keg).rsplit("/", 1)[-1]
                    break
        if product_id is None:
            raise HomeAssistantError(
                "No active PerfectDraft keg product ID is available"
            )

        beer_data: PerfectDraftBeerData = hass.data[DOMAIN][DATA_BEER_DATA]
        await beer_data.async_set_ideal_temperature(product_id, temperature)
        for coordinator in coordinators:
            data = dict(coordinator.data or {})
            data["_beer_data"] = beer_data.snapshot()
            coordinator.async_set_updated_data(data)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_IDEAL_TEMPERATURE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_IDEAL_TEMPERATURE,
            handle_set_ideal_temperature,
            schema=SET_IDEAL_TEMPERATURE_SCHEMA,
        )

    async def handle_refresh_shop_data(call: ServiceCall) -> None:
        product_id = call.data.get(ATTR_PRODUCT_ID)
        coordinators = [
            item
            for key, item in hass.data.get(DOMAIN, {}).items()
            if key != DATA_BEER_DATA
            and isinstance(item, PerfectDraftDataUpdateCoordinator)
        ]
        if product_id is None:
            for coordinator in coordinators:
                active = (coordinator.data or {}).get("_active_keg") or {}
                keg = active.get("keg")
                if keg:
                    product_id = str(keg).rsplit("/", 1)[-1]
                    break
        if product_id is None:
            raise HomeAssistantError(
                "No active PerfectDraft keg product ID is available"
            )

        beer_data: PerfectDraftBeerData = hass.data[DOMAIN][DATA_BEER_DATA]
        refreshed = await beer_data.async_refresh_shop_product(product_id)
        if not refreshed:
            raise HomeAssistantError(
                "Shop data refresh was skipped because the product has no URL "
                "or the rate limit has not elapsed"
            )
        for coordinator in coordinators:
            data = dict(coordinator.data or {})
            data["_beer_data"] = beer_data.snapshot()
            coordinator.async_set_updated_data(data)

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH_SHOP_DATA):
        hass.services.async_register(
            DOMAIN,
            SERVICE_REFRESH_SHOP_DATA,
            handle_refresh_shop_data,
            schema=vol.Schema({vol.Optional(ATTR_PRODUCT_ID): str}),
        )

    async def handle_set_local_beer(call: ServiceCall) -> None:
        product_id = call.data.get(ATTR_PRODUCT_ID)
        coordinators = [
            item
            for key, item in hass.data.get(DOMAIN, {}).items()
            if key != DATA_BEER_DATA
            and isinstance(item, PerfectDraftDataUpdateCoordinator)
        ]
        if product_id is None:
            for coordinator in coordinators:
                active = (coordinator.data or {}).get("_active_keg") or {}
                keg = active.get("keg")
                if keg:
                    product_id = str(keg).rsplit("/", 1)[-1]
                    break
        if product_id is None:
            raise HomeAssistantError(
                "No active PerfectDraft keg product ID is available"
            )

        entry = {
            "name": call.data.get(ATTR_NAME),
            "product_name": call.data.get(ATTR_PRODUCT_NAME),
            "url": call.data.get(ATTR_URL),
            "sku": call.data.get(ATTR_SKU),
            "brewery": call.data.get(ATTR_BREWERY),
            "style": call.data.get(ATTR_STYLE),
            "country": call.data.get(ATTR_COUNTRY),
            "abv": call.data.get(ATTR_ABV),
            "size": call.data.get(ATTR_SIZE),
        }
        if call.data.get(ATTR_TEMPERATURE) is not None:
            entry["serving_temperature"] = f"{call.data[ATTR_TEMPERATURE]:g}°C"

        beer_data: PerfectDraftBeerData = hass.data[DOMAIN][DATA_BEER_DATA]
        await beer_data.async_set_local_catalogue_entry(product_id, entry)
        for coordinator in coordinators:
            data = dict(coordinator.data or {})
            data["_beer_data"] = beer_data.snapshot()
            coordinator.async_set_updated_data(data)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_LOCAL_BEER):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_LOCAL_BEER,
            handle_set_local_beer,
            schema=SET_LOCAL_BEER_SCHEMA,
        )
