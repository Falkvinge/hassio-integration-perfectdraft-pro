"""Config flow for PerfectDraft integration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_MACHINE_ID,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    RECAPTCHA_SITE_KEY,
)
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
)
from .api import PerfectDraftApiClient
from .recaptcha import async_generate_recaptcha_token

_LOGGER = logging.getLogger(__name__)

RECAPTCHA_HTML_PATH = Path(__file__).parent / "static" / "recaptcha.html"
RECAPTCHA_CALLBACK_PATH = "/api/perfectdraft/recaptcha_callback"
RECAPTCHA_PAGE_PATH = "/api/perfectdraft/recaptcha"

_recaptcha_html_cache: str | None = None


def _get_recaptcha_html() -> str:
    global _recaptcha_html_cache
    if _recaptcha_html_cache is None:
        raw = RECAPTCHA_HTML_PATH.read_text()
        _recaptcha_html_cache = raw.replace("RECAPTCHA_SITE_KEY", RECAPTCHA_SITE_KEY)
    return _recaptcha_html_cache


def _register_views(hass: HomeAssistant) -> None:
    """Register the reCAPTCHA views once."""
    key = f"{DOMAIN}_views_registered"
    if hass.data.get(key):
        return
    hass.http.register_view(RecaptchaPageView())
    hass.http.register_view(RecaptchaCallbackView())
    hass.data[key] = True


class RecaptchaPageView(HomeAssistantView):
    """Serve the reCAPTCHA HTML page."""

    url = RECAPTCHA_PAGE_PATH
    name = "api:perfectdraft:recaptcha"
    requires_auth = False

    async def get(self, request):
        return aiohttp.web.Response(
            text=_get_recaptcha_html(),
            content_type="text/html",
        )


class RecaptchaCallbackView(HomeAssistantView):
    """Receive the reCAPTCHA token from the browser and resume the config flow."""

    url = RECAPTCHA_CALLBACK_PATH
    name = "api:perfectdraft:recaptcha_callback"
    requires_auth = False

    async def post(self, request):
        hass = request.app["hass"]
        try:
            data = await request.json()
        except Exception:
            return aiohttp.web.json_response(
                {"error": "invalid body"}, status=400
            )

        flow_id = data.get("flow_id")
        token = data.get("token")
        if not flow_id or not token:
            return aiohttp.web.json_response(
                {"error": "missing flow_id or token"}, status=400
            )

        # Stash the token where the flow can find it, then signal "done"
        hass.data.setdefault(f"{DOMAIN}_recaptcha_tokens", {})[flow_id] = token

        try:
            await hass.config_entries.flow.async_configure(flow_id)
        except Exception:
            _LOGGER.exception("Failed to resume config flow %s", flow_id)
            return aiohttp.web.json_response(
                {"error": "flow error"}, status=500
            )

        return aiohttp.web.json_response({"ok": True})


class PerfectDraftConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PerfectDraft."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._recaptcha_token: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 1: collect email and password."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._password = user_input[CONF_PASSWORD]

            # Try server-side reCAPTCHA token generation first
            session = async_get_clientsession(self.hass)
            token = await async_generate_recaptcha_token(session)
            if token:
                _LOGGER.debug("Server-side reCAPTCHA token obtained")
                self._recaptcha_token = token
                return await self.async_step_finish()

            # Fall back to browser-based external step
            _LOGGER.debug("Server-side reCAPTCHA failed, falling back to browser")
            return await self.async_step_recaptcha()

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

    async def async_step_recaptcha(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 2 (fallback): external step — open browser for reCAPTCHA."""
        _register_views(self.hass)

        callback_url = f"{RECAPTCHA_CALLBACK_PATH}"
        page_url = (
            f"{RECAPTCHA_PAGE_PATH}"
            f"?callback={callback_url}&flow_id={self.flow_id}"
        )

        return self.async_external_step(step_id="recaptcha", url=page_url)

    async def async_step_recaptcha_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Called automatically when the external reCAPTCHA step completes."""
        tokens = self.hass.data.get(f"{DOMAIN}_recaptcha_tokens", {})
        self._recaptcha_token = tokens.pop(self.flow_id, None)

        if not self._recaptcha_token:
            return self.async_abort(reason="recaptcha_failed")

        return self.async_external_step_done(next_step_id="finish")

    async def async_step_finish(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Step 3: authenticate with the API and create the config entry."""
        session = async_get_clientsession(self.hass)
        client = PerfectDraftApiClient(session)

        try:
            await client.authenticate(
                self._email, self._password, self._recaptcha_token
            )
        except AuthenticationError as err:
            _LOGGER.error("Authentication failed: %s", err)
            return self.async_abort(reason="invalid_auth")
        except PerfectDraftConnectionError as err:
            _LOGGER.error("Connection failed: %s", err)
            return self.async_abort(reason="cannot_connect")
        except PerfectDraftApiError as err:
            _LOGGER.error("API error during auth: %s", err)
            return self.async_abort(reason="unknown")

        try:
            profile = await client.get_user_profile()
        except (PerfectDraftApiError, PerfectDraftConnectionError):
            return self.async_abort(reason="cannot_connect")

        machine_id = _extract_machine_id(profile)

        await self.async_set_unique_id(self._email.lower())
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"PerfectDraft ({self._email})",
            data={
                CONF_EMAIL: self._email,
                CONF_ACCESS_TOKEN: client.access_token,
                CONF_ID_TOKEN: client._id_token,
                CONF_REFRESH_TOKEN: client.refresh_token,
                CONF_MACHINE_ID: machine_id,
            },
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
            return await self.async_step_recaptcha()

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
    """Best-effort extraction of the first machine ID from the /api/me response.

    The exact shape is unconfirmed; we try several plausible field names.
    """
    if "machine_id" in profile:
        return profile["machine_id"]

    for key in ("machines", "perfectdraft_machines", "machineIds"):
        machines = profile.get(key)
        if isinstance(machines, list) and machines:
            item = machines[0]
            if isinstance(item, dict):
                return item.get("id") or item.get("machine_id") or item.get("machineId")
            return str(item)

    _LOGGER.warning(
        "Could not extract machine_id from profile response: %s",
        list(profile.keys()),
    )
    return None
