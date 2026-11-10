"""DataUpdateCoordinator for PerfectDraft."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import PerfectDraftApiClient
from .const import (
    CONF_MACHINE_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
    PerfectDraftError,
)

_LOGGER = logging.getLogger(__name__)


def get_setting_id(data: dict[str, Any] | None) -> str | None:
    """Extract the machine setting resource ID from coordinator data."""
    if not isinstance(data, dict):
        return None
    setting = data.get("setting")
    if isinstance(setting, dict):
        if setting.get("id") is not None:
            return str(setting["id"])
        iri = setting.get("@id")
        if isinstance(iri, str) and "/" in iri:
            tail = iri.rstrip("/").rsplit("/", 1)[-1]
            if tail:
                return tail
    machine_id = data.get("_machine_id") or data.get("id")
    return str(machine_id) if machine_id is not None else None


_APPLIANCE_SETTING_KEYS = (
    "temperature",
    "temperatureMin",
    "temperatureMax",
    "temperatureUnit",
    "ecoModeEnabled",
    "ecoModeSchedulerEnabled",
)


def reconcile_settings(
    api_setting: dict[str, Any] | None,
    details_settings: dict[str, Any] | None,
    prev_updated_at: str | None,
    sync_state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str | None]:
    """Reconcile the cloud setting resource with the live appliance shadow.

    Tracks which source (`api_setting` vs `details_settings`) changed most
    recently so stale telemetry in `details_settings` never reverts a newer
    setting from the mobile app or Home Assistant, while changes made directly
    on the appliance shadow (`details_settings`) are immediately reflected.
    """
    raw_api: dict[str, Any] = (
        dict(api_setting) if isinstance(api_setting, dict) else {}
    )
    merged: dict[str, Any] = dict(raw_api)
    hw: dict[str, Any] = (
        dict(details_settings) if isinstance(details_settings, dict) else {}
    )

    updated_at = merged.get("updatedAt")
    updated_at_str = str(updated_at) if updated_at is not None else None
    api_changed = (
        prev_updated_at is not None
        and updated_at_str is not None
        and updated_at_str != prev_updated_at
    )

    stale_hw: dict[str, Any] = {}
    prev_api: dict[str, Any] | None = None
    prev_hw: dict[str, Any] | None = None
    if isinstance(sync_state, dict):
        prev_api = sync_state.get("prev_api")
        prev_hw = sync_state.get("prev_hw")
        stale_hw = sync_state.setdefault("stale_hw", {})
        if not api_changed and isinstance(prev_api, dict):
            for key in (
                "mode",
                "boost",
                "ecoModeEnabled",
                "ecoModeSchedulerEnabled",
                "temperature",
                "ecoModeBeerTemperatureSetPoint",
            ):
                if raw_api.get(key) != prev_api.get(key):
                    api_changed = True
                    break

    if api_changed:
        if (
            isinstance(prev_api, dict)
            and prev_api.get("mode") in ("eco", "cooling", "boost")
            and raw_api.get("mode") == "standard"
            and raw_api.get("ecoModeEnabled") is True
        ):
            merged["ecoModeEnabled"] = False

        if (
            merged.get("mode") == "cooling"
            and merged.get("ecoModeSchedulerEnabled") is None
        ):
            merged["ecoModeSchedulerEnabled"] = True

        for key in _APPLIANCE_SETTING_KEYS:
            if key in hw and hw[key] is not None:
                hw_just_changed = (
                    isinstance(prev_hw, dict)
                    and hw.get(key) != prev_hw.get(key)
                )
                if (
                    not hw_just_changed
                    and key in merged
                    and merged[key] is not None
                    and hw[key] != merged[key]
                ):
                    stale_hw[key] = hw[key]

    for key in _APPLIANCE_SETTING_KEYS:
        if key in hw and hw[key] is not None:
            if key in stale_hw:
                if hw[key] != stale_hw[key]:
                    stale_hw.pop(key, None)
                    merged[key] = hw[key]
                else:
                    continue
            else:
                merged[key] = hw[key]

    if (
        merged.get("mode") == "cooling"
        and merged.get("ecoModeSchedulerEnabled") is None
    ):
        merged["ecoModeSchedulerEnabled"] = True

    if isinstance(sync_state, dict):
        sync_state["prev_api"] = raw_api
        sync_state["prev_hw"] = hw

    return merged, updated_at_str or prev_updated_at


class PerfectDraftDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Single coordinator that polls the PerfectDraft API for all entities."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: PerfectDraftApiClient,
        config_entry: ConfigEntry,
    ) -> None:
        self.client = client
        self._prev_setting_updated_at: str | None = None
        self._setting_sync_state: dict[str, Any] = {}
        interval = config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            config_entry=config_entry,
        )

    def update_interval_from_options(self) -> None:
        """Re-read the polling interval from config entry options."""
        interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        self.update_interval = timedelta(seconds=interval)
        _LOGGER.debug("Polling interval updated to %s seconds", interval)

    async def _async_update_data(self) -> dict[str, Any]:
        machine_id = self.config_entry.data.get(CONF_MACHINE_ID)

        try:
            if not machine_id:
                profile = await self.client.get_user_profile()
                machines = profile.get("perfectdraftMachines", [])
                if not machines:
                    raise UpdateFailed(
                        "No PerfectDraft machine found on this account"
                    )
                machine_id = str(machines[0].get("id", ""))

            details = await self.client.get_machine_details(machine_id)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Authentication failed — please re-authenticate"
            ) from err
        except (PerfectDraftApiError, PerfectDraftConnectionError) as err:
            raise UpdateFailed(str(err)) from err

        details["_machine_id"] = machine_id

        merged_setting: dict[str, Any] = (
            dict(details["setting"])
            if isinstance(details.get("setting"), dict)
            else {}
        )

        setting_id = get_setting_id(details)
        if setting_id:
            try:
                full_setting = await self.client.get_machine_settings(setting_id)
                if isinstance(full_setting, dict):
                    merged_setting.update(full_setting)
            except (PerfectDraftApiError, PerfectDraftConnectionError) as err:
                _LOGGER.debug("Full machine setting lookup failed: %s", err)

        details_payload = details.get("details")
        details_settings = (
            details_payload.get("settings")
            if isinstance(details_payload, dict)
            else None
        )
        reconciled_setting, self._prev_setting_updated_at = reconcile_settings(
            merged_setting,
            details_settings,
            self._prev_setting_updated_at,
            self._setting_sync_state,
        )
        details["setting"] = reconciled_setting

        # The active keg lives behind a separate serialization group. Treat it
        # as best-effort so a failure here doesn't take the whole device down.
        try:
            active = await self.client.get_machine_active_keg(machine_id)
            details["kegActive"] = active.get("kegActive")
        except (PerfectDraftApiError, PerfectDraftConnectionError) as err:
            _LOGGER.debug("Active keg lookup failed: %s", err)

        return details

    async def async_update_settings(self, **changes: Any) -> None:
        """Update machine settings via the API and refresh from the real server state."""
        data = self.data or {}
        setting_id = get_setting_id(data) or self.config_entry.data.get(CONF_MACHINE_ID)
        if not setting_id:
            raise HomeAssistantError("PerfectDraft setting ID is unavailable")

        current_setting = (
            dict(data["setting"]) if isinstance(data.get("setting"), dict) else {}
        )
        try:
            updated = await self.client.update_machine_settings(
                setting_id, current_setting, **changes
            )
        except PerfectDraftError as err:
            self.async_update_listeners()
            raise HomeAssistantError(
                f"Failed to update PerfectDraft settings: {err}"
            ) from err

        if isinstance(self.data, dict) and isinstance(updated, dict):
            merged = dict(current_setting)
            merged.update(updated)
            self.data["setting"] = merged
            self.async_update_listeners()

        await self.async_request_refresh()

    async def async_set_active_keg(self, product_id: int) -> None:
        """Set the active keg via the API and refresh from the real server state."""
        data = self.data or {}
        machine_id = data.get("_machine_id") or self.config_entry.data.get(
            CONF_MACHINE_ID
        )
        if not machine_id:
            raise HomeAssistantError("PerfectDraft machine ID is unavailable")

        now = datetime.now(timezone.utc)
        try:
            created = await self.client.set_active_keg(
                machine_id, int(product_id), now
            )
        except PerfectDraftError as err:
            self.async_update_listeners()
            raise HomeAssistantError(
                f"Failed to set active PerfectDraft keg: {err}"
            ) from err

        if isinstance(self.data, dict) and isinstance(created, dict):
            keg_active = dict(self.data.get("kegActive") or {})
            if created.get("keg"):
                keg_active["keg"] = created["keg"]
            if created.get("insertedAt"):
                keg_active["insertedAt"] = created["insertedAt"]
            if keg_active:
                self.data["kegActive"] = keg_active
                self.async_update_listeners()

        await self.async_request_refresh()
