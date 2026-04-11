"""Async API client for the PerfectDraft cloud service."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_KEY, RECAPTCHA_ACTION
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
)

_LOGGER = logging.getLogger(__name__)



class PerfectDraftApiClient:
    """Async client for api.perfectdraft.com."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._base = API_BASE_URL
        self._access_token: str | None = None
        self._id_token: str | None = None
        self._refresh_token: str | None = None

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    def set_tokens(
        self,
        access_token: str,
        id_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Restore tokens from persisted config entry data."""
        self._access_token = access_token
        if id_token is not None:
            self._id_token = id_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

    async def authenticate(
        self, email: str, password: str, recaptcha_token: str
    ) -> dict[str, str]:
        """Sign in and return the token triple.

        Returns dict with keys AccessToken, IdToken, RefreshToken.
        """
        url = f"{self._base}/authentication/sign-in"
        payload = {
            "email": email,
            "password": password,
            "recaptchaToken": recaptcha_token,
            "recaptchaAction": RECAPTCHA_ACTION,
        }
        headers = {"x-api-key": API_KEY}

        try:
            async with self._session.post(
                url, json=payload, headers=headers
            ) as resp:
                if resp.status == 401 or resp.status == 403:
                    body = await resp.text()
                    raise AuthenticationError(
                        f"Sign-in rejected ({resp.status}): {body}"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise PerfectDraftApiError(resp.status, body)
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise PerfectDraftConnectionError(str(exc)) from exc

        self._access_token = data["AccessToken"]
        self._id_token = data["IdToken"]
        self._refresh_token = data["RefreshToken"]

        _LOGGER.debug("Authenticated successfully")
        return data

    async def refresh_access_token(
        self, refresh_token: str | None = None
    ) -> dict[str, str]:
        """Use the refresh token to obtain a new access token.

        The exact endpoint is not yet confirmed; we try the most likely
        candidates based on the API's Cognito-style token pattern.
        """
        token = refresh_token or self._refresh_token
        if not token:
            raise AuthenticationError("No refresh token available")

        url = f"{self._base}/authentication/refresh"
        payload = {"refreshToken": token}
        headers = {"x-api-key": API_KEY}

        try:
            async with self._session.post(
                url, json=payload, headers=headers
            ) as resp:
                if resp.status in (401, 403):
                    raise AuthenticationError("Refresh token expired or invalid")
                if resp.status != 200:
                    body = await resp.text()
                    raise PerfectDraftApiError(resp.status, body)
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise PerfectDraftConnectionError(str(exc)) from exc

        self._access_token = data.get("AccessToken", self._access_token)
        self._id_token = data.get("IdToken", self._id_token)
        if "RefreshToken" in data:
            self._refresh_token = data["RefreshToken"]

        _LOGGER.debug("Token refreshed successfully")
        return data

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an authenticated API request with automatic 401 retry."""
        url = f"{self._base}{path}"
        headers = kwargs.pop("headers", {})
        headers["x-access-token"] = self._access_token or ""

        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as resp:
                if resp.status == 401:
                    _LOGGER.debug("Got 401, attempting token refresh")
                    await self.refresh_access_token()
                    headers["x-access-token"] = self._access_token or ""
                    async with self._session.request(
                        method, url, headers=headers, **kwargs
                    ) as retry_resp:
                        if retry_resp.status == 401:
                            raise AuthenticationError(
                                "Still unauthorized after token refresh"
                            )
                        if retry_resp.status == 429:
                            raise PerfectDraftApiError(429, "Rate limited")
                        if retry_resp.status >= 400:
                            body = await retry_resp.text()
                            raise PerfectDraftApiError(retry_resp.status, body)
                        return await retry_resp.json()

                if resp.status == 429:
                    raise PerfectDraftApiError(429, "Rate limited")
                if resp.status >= 400:
                    body = await resp.text()
                    raise PerfectDraftApiError(resp.status, body)
                return await resp.json()
        except aiohttp.ClientError as exc:
            raise PerfectDraftConnectionError(str(exc)) from exc

    async def get_user_profile(self) -> dict[str, Any]:
        """GET /api/me — returns user profile including machine IDs."""
        return await self._request("GET", "/api/me")

    async def get_machine_details(self, machine_id: str) -> dict[str, Any]:
        """GET /api/perfectdraft_machines/{machine_id} — full machine status."""
        return await self._request(
            "GET", f"/api/perfectdraft_machines/{machine_id}"
        )
