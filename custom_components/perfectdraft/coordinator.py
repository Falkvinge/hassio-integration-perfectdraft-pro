"""DataUpdateCoordinator for PerfectDraft."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
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
)

_LOGGER = logging.getLogger(__name__)


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
                machine_id = _extract_first_machine_id(profile)
                if not machine_id:
                    raise UpdateFailed(
                        "No PerfectDraft machine found on this account"
                    )

            details = await self.client.get_machine_details(machine_id)
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(
                "Authentication failed — please re-authenticate"
            ) from err
        except (PerfectDraftApiError, PerfectDraftConnectionError) as err:
            raise UpdateFailed(str(err)) from err

        details["_machine_id"] = machine_id
        return details


def _extract_first_machine_id(profile: dict[str, Any]) -> str | None:
    """Best-effort extraction of the first machine ID from /api/me."""
    if "machine_id" in profile:
        return profile["machine_id"]

    for key in ("machines", "perfectdraft_machines", "machineIds"):
        machines = profile.get(key)
        if isinstance(machines, list) and machines:
            item = machines[0]
            if isinstance(item, dict):
                return (
                    item.get("id")
                    or item.get("machine_id")
                    or item.get("machineId")
                )
            return str(item)
    return None
