"""Persistent beer metadata overrides and shop cache."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .catalogue import PERFECTDRAFT_CATALOGUE, lookup_product
from .const import DOMAIN
from .shop import async_fetch_available_beer_catalogue, async_fetch_shop_product

_LOGGER = logging.getLogger(__name__)

STORE_VERSION = 1
STORE_KEY = f"{DOMAIN}_beer_data"
CURRENT_BEER_REFRESH = timedelta(hours=12)
FAVORITE_BEER_REFRESH = timedelta(hours=24)
MIN_FETCH_GAP = timedelta(seconds=60)
BACK_IN_STOCK_WINDOW = timedelta(days=7)
AVAILABLE_BEERS_REFRESH = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(UTC)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class PerfectDraftBeerData:
    """Manage local beer overrides and low-frequency product-page cache."""

    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession) -> None:
        self._hass = hass
        self._session = session
        self._store: Store[dict[str, Any]] = Store(hass, STORE_VERSION, STORE_KEY)
        self._data: dict[str, Any] = {
            "catalogue": {},
            "ideal_temperature_overrides": {},
            "local_catalogue": {},
            "shop_cache": {},
            "available_beers": {},
            "job_status": {"status": "idle"},
            "last_shop_fetch": None,
        }

    async def async_load(self) -> None:
        """Load persisted beer data."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self._data.update(stored)
        if self._seed_catalogue():
            await self.async_save()

    def _seed_catalogue(self) -> bool:
        """Add shipped catalogue entries without overwriting local data."""
        catalogue = dict(self._data.get("catalogue") or {})
        changed = False
        for product_id, entry in PERFECTDRAFT_CATALOGUE.items():
            existing = dict(catalogue.get(product_id) or {})
            seeded = dict(existing)
            for key, value in entry.items():
                if key not in seeded:
                    seeded[key] = value
            if "catalogue_source" not in seeded:
                seeded["catalogue_source"] = "static"
            if seeded != existing:
                catalogue[product_id] = seeded
                changed = True
        self._data["catalogue"] = catalogue
        return changed

    async def async_save(self) -> None:
        """Persist beer data."""
        await self._store.async_save(self._data)

    def snapshot(self) -> dict[str, Any]:
        """Return a shallow snapshot safe to expose through coordinator data."""
        return {
            "catalogue": dict(self._data.get("catalogue") or {}),
            "ideal_temperature_overrides": dict(
                self._data.get("ideal_temperature_overrides") or {}
            ),
            "local_catalogue": dict(self._data.get("local_catalogue") or {}),
            "shop_cache": dict(self._data.get("shop_cache") or {}),
            "available_beers": dict(self._data.get("available_beers") or {}),
            "job_status": dict(self._data.get("job_status") or {"status": "idle"}),
            "last_shop_fetch": self._data.get("last_shop_fetch"),
        }

    async def async_set_job_status(
        self,
        status: str,
        *,
        job_type: str | None = None,
        current_item: str | None = None,
        processed: int | None = None,
        total: int | None = None,
        last_error: str | None = None,
    ) -> None:
        """Persist a user-visible catalogue/metadata job status."""
        now = _now().isoformat()
        previous = self._data.get("job_status") or {}
        started_at = previous.get("started_at")
        if status == "running":
            started_at = now

        processed_value = processed if processed is not None else previous.get("processed")
        total_value = total if total is not None else previous.get("total")
        percent = None
        if processed_value is not None and total_value:
            percent = round(float(processed_value) / float(total_value) * 100, 1)

        job = {
            "status": status,
            "job_type": job_type if job_type is not None else previous.get("job_type"),
            "current_item": (
                current_item if current_item is not None else previous.get("current_item")
            ),
            "processed": processed_value,
            "total": total_value,
            "percent": percent,
            "started_at": started_at,
            "updated_at": now,
            "last_success": previous.get("last_success"),
            "last_error": last_error,
        }
        if status == "completed":
            job["last_success"] = now
        if status not in {"failed", "skipped"}:
            job["last_error"] = None
        self._data["job_status"] = {
            key: value for key, value in job.items() if value is not None
        }
        await self.async_save()

    def ideal_temperature_override(self, product_id: str | None) -> float | None:
        """Return the manually set ideal temperature for a product."""
        if not product_id:
            return None
        value = (self._data.get("ideal_temperature_overrides") or {}).get(product_id)
        return float(value) if value is not None else None

    async def async_set_ideal_temperature(
        self,
        product_id: str,
        temperature: float,
    ) -> None:
        """Store a manual ideal temperature override for a beer."""
        self._data.setdefault("ideal_temperature_overrides", {})[product_id] = float(
            temperature
        )
        await self.async_save()

    async def async_set_local_catalogue_entry(
        self,
        product_id: str,
        entry: dict[str, Any],
    ) -> None:
        """Store or update a user-local catalogue entry for a beer."""
        existing = dict(
            (self._data.get("local_catalogue") or {}).get(product_id) or {}
        )
        existing.update(
            {
                key: value
                for key, value in entry.items()
                if value not in (None, "")
            }
        )
        existing["local_catalogue"] = True
        existing["catalogue_source"] = "local"
        existing["product_id"] = product_id
        existing["updated_at"] = _now().isoformat()
        self._data.setdefault("local_catalogue", {})[product_id] = existing
        catalogue_entry = dict((self._data.get("catalogue") or {}).get(product_id) or {})
        catalogue_entry.update(existing)
        self._data.setdefault("catalogue", {})[product_id] = catalogue_entry
        await self.async_save()

    async def async_update_shop_cache(
        self,
        product_ids: list[str],
        current_product_id: str | None,
    ) -> None:
        """Refresh at most one stale product-page cache entry per coordinator cycle."""
        await self.async_update_available_beers()
        due_product_id = self._first_due_product_id(product_ids, current_product_id)
        if due_product_id is None:
            return
        await self.async_refresh_shop_product(due_product_id)

    async def async_update_available_beers(self, *, force: bool = False) -> bool:
        """Refresh the curated PerfectDraft keg count and names slowly."""
        current = self._data.get("available_beers") or {}
        last_checked = _parse_iso(current.get("last_checked"))
        if (
            not force
            and last_checked
            and _now() - last_checked < AVAILABLE_BEERS_REFRESH
        ):
            return False

        try:
            data = await async_fetch_available_beer_catalogue(self._session)
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Unable to refresh PerfectDraft available beer list: %s", err)
            return False

        data["last_checked"] = _now().isoformat()
        self._data["available_beers"] = data
        await self.async_save()
        return True

    async def async_refresh_active_and_favorite_metadata(
        self,
        product_ids: list[str],
        current_product_id: str | None,
    ) -> bool:
        """Refresh one active/favourite product, choosing the stalest first."""
        due_product_id = self._first_due_product_id(product_ids, current_product_id)
        if due_product_id is None:
            ordered = [current_product_id, *product_ids]
            due_product_id = next((product_id for product_id in ordered if product_id), None)
        if due_product_id is None:
            return False
        return await self.async_refresh_shop_product(due_product_id)

    async def async_refresh_shop_product(self, product_id: str) -> bool:
        """Refresh one product-page cache entry, respecting the fetch gap."""
        last_fetch = _parse_iso(self._data.get("last_shop_fetch"))
        if last_fetch and _now() - last_fetch < MIN_FETCH_GAP:
            return False

        url = lookup_product(product_id).get("url")
        if not url:
            return False

        try:
            shop_data = await async_fetch_shop_product(self._session, str(url))
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug(
                "Unable to refresh PerfectDraft shop data for %s: %s",
                product_id,
                err,
            )
            return False

        fetched_at = _now().isoformat()
        previous = (self._data.get("shop_cache") or {}).get(product_id) or {}
        self._apply_stock_transition(product_id, previous, shop_data, fetched_at)
        shop_data["shop_last_checked"] = fetched_at
        self._data.setdefault("shop_cache", {})[product_id] = shop_data
        catalogue_entry = dict((self._data.get("catalogue") or {}).get(product_id) or {})
        catalogue_entry.update(shop_data)
        self._data.setdefault("catalogue", {})[product_id] = catalogue_entry
        self._data["last_shop_fetch"] = fetched_at
        await self.async_save()
        return True

    def _apply_stock_transition(
        self,
        product_id: str,
        previous: dict[str, Any],
        current: dict[str, Any],
        fetched_at: str,
    ) -> None:
        """Mark a product as back in stock for a short window after recovery."""
        previous_state = previous.get("stock_state")
        current_state = current.get("stock_state")
        back_in_stock_since = previous.get("back_in_stock_since")

        if previous_state == "out_of_stock" and current_state == "in_stock":
            back_in_stock_since = fetched_at

        since = _parse_iso(back_in_stock_since)
        if current_state == "in_stock" and since and _now() - since <= BACK_IN_STOCK_WINDOW:
            current["back_in_stock"] = True
            current["back_in_stock_since"] = since.isoformat()
            current["back_in_stock_until"] = (since + BACK_IN_STOCK_WINDOW).isoformat()
            return

        current["back_in_stock"] = False
        if current_state == "out_of_stock":
            current.pop("back_in_stock_since", None)
            current.pop("back_in_stock_until", None)

    def _first_due_product_id(
        self,
        product_ids: list[str],
        current_product_id: str | None,
    ) -> str | None:
        """Return the next product due for refresh, current beer first."""
        seen: set[str] = set()
        ordered = []
        for product_id in [current_product_id, *product_ids]:
            if product_id and product_id not in seen:
                ordered.append(product_id)
                seen.add(product_id)

        cache = self._data.get("shop_cache") or {}
        now = _now()
        for product_id in ordered:
            entry = cache.get(product_id) or {}
            last_checked = _parse_iso(entry.get("shop_last_checked"))
            ttl = (
                CURRENT_BEER_REFRESH
                if product_id == current_product_id
                else FAVORITE_BEER_REFRESH
            )
            if last_checked is None or now - last_checked >= ttl:
                return product_id
        return None
