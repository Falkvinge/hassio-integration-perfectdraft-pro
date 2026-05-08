"""Shared entity helpers for PerfectDraft."""
from __future__ import annotations

from typing import Any

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from .catalogue import lookup_product
from .const import DOMAIN
from .coordinator import PerfectDraftDataUpdateCoordinator


def device_info(coordinator: PerfectDraftDataUpdateCoordinator) -> DeviceInfo:
    """Return the Home Assistant device info for the configured machine."""
    data = coordinator.data or {}
    machine_id = data.get("_machine_id", "unknown")
    details = data.get("details") or {}
    return DeviceInfo(
        identifiers={(DOMAIN, str(machine_id))},
        name="PerfectDraft Pro",
        manufacturer="PerfectDraft",
        model="Pro",
        sw_version=details.get("firmwareVersion"),
        serial_number=details.get("serialNumber"),
    )


def setting(coordinator: PerfectDraftDataUpdateCoordinator) -> dict[str, Any]:
    """Return the current setting payload."""
    return (coordinator.data or {}).get("setting") or {}


def active_keg(coordinator: PerfectDraftDataUpdateCoordinator) -> dict[str, Any]:
    """Return active keg metadata."""
    return (coordinator.data or {}).get("_active_keg") or {}


def product_id_from_ref(product_ref: Any) -> str | None:
    """Extract a product ID from an API product reference."""
    if product_ref is None:
        return None
    if isinstance(product_ref, dict):
        product_ref = product_ref.get("@id") or product_ref.get("id")
    if product_ref is None:
        return None
    return str(product_ref).rsplit("/", 1)[-1]


def active_product_id(coordinator: PerfectDraftDataUpdateCoordinator) -> str | None:
    """Return the active keg product ID."""
    return product_id_from_ref(active_keg(coordinator).get("keg"))


def catalogue_value(product_id: str | None, key: str) -> Any:
    """Return a normalised catalogue value."""
    value = lookup_product(product_id).get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def catalogue_attributes(product_id: str | None) -> dict[str, Any]:
    """Return useful catalogue metadata as flat HA attributes."""
    catalogue = lookup_product(product_id)
    attrs: dict[str, Any] = {"product_id": product_id}
    for key in (
        "name",
        "product_name",
        "sku",
        "url",
        "brewery",
        "style",
        "country",
        "abv",
        "size",
        "serving_temperature",
    ):
        value = catalogue.get(key)
        if isinstance(value, dict):
            value = value.get("value")
        if value not in (None, ""):
            attrs[key] = value
    return attrs


def favorite_product_ids(data: dict[str, Any]) -> list[str]:
    """Return de-duplicated favourite product IDs from /api/me."""
    profile = data.get("_profile") or {}
    ratings = profile.get("customerProductRatings") or []
    favorites: list[str] = []
    seen_beers: set[str] = set()
    for rating in ratings:
        if not isinstance(rating, dict):
            continue
        if rating.get("active") is False or rating.get("removedAt"):
            continue
        if rating.get("favourite") is not True:
            continue
        product_id = product_id_from_ref(rating.get("keg"))
        if not product_id:
            continue
        dedupe_key = str(catalogue_value(product_id, "name") or product_id).casefold()
        if dedupe_key not in seen_beers:
            favorites.append(product_id)
            seen_beers.add(dedupe_key)
    return favorites


async def update_setting(
    coordinator: PerfectDraftDataUpdateCoordinator,
    updates: dict[str, Any],
) -> None:
    """Update the machine setting and refresh coordinator data."""
    current = setting(coordinator)
    setting_id = current.get("id")
    if setting_id is None:
        raise HomeAssistantError("PerfectDraft setting ID is unavailable")

    await coordinator.client.update_machine_setting(str(setting_id), current, updates)
    await coordinator.async_request_refresh()
