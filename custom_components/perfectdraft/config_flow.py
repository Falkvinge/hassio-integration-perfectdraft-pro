"""Config flow for PerfectDraft integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
)
from .api import PerfectDraftApiClient

_LOGGER = logging.getLogger(__name__)


class PerfectDraftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PerfectDraft."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._user_id: str | None = None
        self._refresh_token: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: collect email (for display/unique ID)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            return await self.async_step_tokens()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                }
            ),
            errors=errors,
        )

    async def async_step_tokens(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2: collect UserId and RefreshToken, validate via refresh."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._user_id = user_input[CONF_USER_ID].strip()
            self._refresh_token = user_input[CONF_REFRESH_TOKEN].strip()

            session = async_get_clientsession(self.hass)
            client = PerfectDraftApiClient(session)

            try:
                data = await client.refresh_access_token(
                    user_id=self._user_id,
                    refresh_token=self._refresh_token,
                )
            except AuthenticationError as err:
                _LOGGER.error("Token validation failed: %s", err)
                errors["base"] = "invalid_auth"
            except PerfectDraftConnectionError as err:
                _LOGGER.error("Connection failed: %s", err)
                errors["base"] = "cannot_connect"
            except PerfectDraftApiError as err:
                _LOGGER.error("API error during validation: %s", err)
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(self._email.lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"PerfectDraft ({self._email})",
                    data={
                        CONF_EMAIL: self._email,
                        CONF_USER_ID: self._user_id,
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_ID_TOKEN: data.get("IdToken"),
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )

        return self.async_show_form(
            step_id="tokens",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USER_ID): str,
                    vol.Required(CONF_REFRESH_TOKEN): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        """Handle re-authentication when the refresh token expires."""
        self._email = entry_data.get(CONF_EMAIL)
        self._user_id = entry_data.get(CONF_USER_ID)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Ask user to re-enter tokens for reauth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_id = user_input[CONF_USER_ID].strip()
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()

            session = async_get_clientsession(self.hass)
            client = PerfectDraftApiClient(session)

            try:
                await client.refresh_access_token(
                    user_id=user_id,
                    refresh_token=refresh_token,
                )
            except (AuthenticationError, PerfectDraftApiError, PerfectDraftConnectionError) as err:
                _LOGGER.error("Reauth failed: %s", err)
                errors["base"] = "invalid_auth"
            else:
                self.hass.config_entries.async_update_entry(
                    self.context["entry"],
                    data={
                        **self.context["entry"].data,
                        CONF_USER_ID: user_id,
                        CONF_ACCESS_TOKEN: client.access_token,
                        CONF_REFRESH_TOKEN: client.refresh_token,
                    },
                )
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_ID, default=self._user_id or ""
                    ): str,
                    vol.Required(CONF_REFRESH_TOKEN): str,
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
