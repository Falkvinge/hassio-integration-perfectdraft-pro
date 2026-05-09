"""Shared entity helpers for PerfectDraft."""
from __future__ import annotations

import re
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


def _runtime_beer_data(data: dict[str, Any] | None) -> dict[str, Any]:
    return (data or {}).get("_beer_data") or {}


def local_catalogue_entry(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a user-local catalogue entry for a product."""
    if not product_id:
        return {}
    value = (_runtime_beer_data(data).get("local_catalogue") or {}).get(product_id)
    return value if isinstance(value, dict) else {}


def catalogue_entry(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the runtime catalogue entry, with static fallback."""
    if not product_id:
        return {}
    runtime_catalogue = _runtime_beer_data(data).get("catalogue") or {}
    entry = dict(runtime_catalogue.get(product_id) or lookup_product(product_id))
    if product_id not in runtime_catalogue:
        entry.update(local_catalogue_entry(product_id, data))
    return entry


def runtime_catalogue_value(
    product_id: str | None,
    key: str,
    data: dict[str, Any] | None = None,
) -> Any:
    """Return a catalogue value including user-local overrides."""
    value = catalogue_entry(product_id, data).get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def shop_data(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return cached shop data for a product from coordinator data."""
    if not product_id:
        return {}
    cache = (_runtime_beer_data(data).get("shop_cache") or {})
    value = cache.get(product_id)
    return value if isinstance(value, dict) else {}


def temperature_from_text(value: Any) -> float | None:
    """Return the first numeric temperature from catalogue text."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group(0)) if match else None


def ideal_temperature(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> float | None:
    """Return manual override or catalogue/shop recommended temperature."""
    if not product_id:
        return None

    overrides = _runtime_beer_data(data).get("ideal_temperature_overrides") or {}
    if product_id in overrides:
        return temperature_from_text(overrides[product_id])

    value = runtime_catalogue_value(product_id, "serving_temperature", data)
    if value in (None, ""):
        value = shop_data(product_id, data).get("recommended_temperature")
    return temperature_from_text(value)


def ideal_temperature_source(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> str | None:
    """Return where the ideal temperature came from."""
    if not product_id:
        return None
    overrides = _runtime_beer_data(data).get("ideal_temperature_overrides") or {}
    if product_id in overrides:
        return "manual"
    if runtime_catalogue_value(product_id, "serving_temperature", data) not in (
        None,
        "",
    ):
        return "catalogue"
    if shop_data(product_id, data).get("recommended_temperature") not in (None, ""):
        return "shop"
    return None


def catalogue_attributes(
    product_id: str | None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return useful catalogue metadata as flat HA attributes."""
    catalogue = catalogue_entry(product_id, data)
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
    temp = ideal_temperature(product_id, data)
    if temp is not None:
        attrs["ideal_temperature"] = temp
        attrs["ideal_temperature_source"] = ideal_temperature_source(product_id, data)

    for key in (
        "website_product_id",
        "gtin",
        "sap_product_code",
        "image_url",
        "food_pairings",
        "short_description",
        "plato",
        "recommended_temperature",
        "price",
        "price_currency",
        "price_per_pint",
        "stock_state",
        "stock_quantity",
        "back_in_stock",
        "back_in_stock_since",
        "back_in_stock_until",
        "review_count",
        "review_rating",
        "shop_last_checked",
    ):
        value = shop_data(product_id, data).get(key)
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
