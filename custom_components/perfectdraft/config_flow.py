"""Config flow for PerfectDraft integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PerfectDraftApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_MACHINE_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
)

_LOGGER = logging.getLogger(__name__)

CONF_RECAPTCHA_TOKEN = "recaptcha_token"


class PerfectDraftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PerfectDraft."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: collect email and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            return await self.async_step_token()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    async def async_step_token(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: collect reCAPTCHA token from user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            recaptcha_token = user_input[CONF_RECAPTCHA_TOKEN].strip()

            session = async_get_clientsession(self.hass)
            client = PerfectDraftApiClient(session)

            try:
                await client.authenticate(
                    self._email, self._password, recaptcha_token
                )
            except AuthenticationError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except PerfectDraftConnectionError as err:
                _LOGGER.error("Connection failed: %s", err)
                errors["base"] = "cannot_connect"
            except PerfectDraftApiError as err:
                _LOGGER.error("API error during auth: %s", err)
                errors["base"] = "unknown"
            else:
                try:
                    profile = await client.get_user_profile()
                except (PerfectDraftApiError, PerfectDraftConnectionError):
                    errors["base"] = "cannot_connect"
                else:
                    machine_id = _extract_machine_id(profile)

                    await self.async_set_unique_id(self._email.lower())
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"PerfectDraft ({self._email})",
                        data={
                            CONF_EMAIL: self._email,
                            CONF_ACCESS_TOKEN: client.access_token,
                            CONF_ID_TOKEN: client.id_token,
                            CONF_REFRESH_TOKEN: client.refresh_token,
                            CONF_MACHINE_ID: machine_id,
                        },
                    )

        return self.async_show_form(
            step_id="token",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RECAPTCHA_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle re-authentication when the refresh token expires."""
        self._email = entry_data.get(CONF_EMAIL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask user to re-enter credentials for reauth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]
            return await self.async_step_token()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL, default=self._email): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PerfectDraftOptionsFlow:
        return PerfectDraftOptionsFlow(config_entry)


class PerfectDraftOptionsFlow(config_entries.OptionsFlow):
    """Handle options for PerfectDraft (polling interval)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            interval = max(user_input[CONF_SCAN_INTERVAL], MIN_SCAN_INTERVAL)
            return self.async_create_entry(
                title="", data={CONF_SCAN_INTERVAL: interval}
            )

        current = self._config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SCAN_INTERVAL, default=current): vol.All(
                        int, vol.Range(min=MIN_SCAN_INTERVAL)
                    ),
                }
            ),
        )


def _extract_machine_id(profile: dict[str, Any]) -> str | None:
    """Extract the first machine ID from the /api/me response."""
    machines = profile.get("perfectdraftMachines")
    if isinstance(machines, list) and machines:
        return str(machines[0].get("id", ""))
    return None
