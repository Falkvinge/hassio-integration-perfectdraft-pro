"""Async API client for the PerfectDraft cloud service."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL, API_KEY, COGNITO_CLIENT_ID, COGNITO_REGION
from .exceptions import (
    AuthenticationError,
    PerfectDraftApiError,
    PerfectDraftConnectionError,
)

_LOGGER = logging.getLogger(__name__)

RECAPTCHA_ACTION_SIGN_IN = "Magento/login"
COGNITO_IDP_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
SETTING_WRITE_FIELDS = (
    "temperature",
    "temperatureMin",
    "temperatureMax",
    "temperatureUnit",
    "pressure",
    "boost",
    "volumeThreshold",
    "ecoModeEnabled",
    "ecoModeBeerTemperatureSetPoint",
    "ecoModeSchedulerEnabled",
    "ecoModeAbortedByAppliance",
    "mode",
)


class PerfectDraftApiClient:
    """Async client for api.perfectdraft.com with Cognito token refresh."""

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

    @property
    def id_token(self) -> str | None:
        return self._id_token

    def set_tokens(
        self,
        access_token: str | None = None,
        id_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        """Restore tokens from persisted config entry data."""
        if access_token is not None:
            self._access_token = access_token
        if id_token is not None:
            self._id_token = id_token
        if refresh_token is not None:
            self._refresh_token = refresh_token

    async def authenticate(
        self, email: str, password: str, recaptcha_token: str
    ) -> dict[str, str]:
        """Sign in via /authentication/sign-in with a reCAPTCHA token.

        The token must be generated from a real browser on perfectdraft.com
        using the web reCAPTCHA Enterprise key with action Magento/login.
        """
        url = f"{self._base}/authentication/sign-in"
        payload = {
            "email": email,
            "password": password,
            "recaptchaToken": recaptcha_token,
            "recaptchaAction": RECAPTCHA_ACTION_SIGN_IN,
        }
        headers = {"x-api-key": API_KEY}

        try:
            async with self._session.post(
                url, json=payload, headers=headers
            ) as resp:
                if resp.status in (400, 401, 403):
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

    async def refresh_access_token(self) -> dict[str, Any]:
        """Refresh tokens directly via AWS Cognito (bypasses API gateway + reCAPTCHA)."""
        if not self._refresh_token:
            raise AuthenticationError("No refresh token available")

        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
        }
        payload = {
            "AuthFlow": "REFRESH_TOKEN_AUTH",
            "ClientId": COGNITO_CLIENT_ID,
            "AuthParameters": {
                "REFRESH_TOKEN": self._refresh_token,
            },
        }

        try:
            async with self._session.post(
                COGNITO_IDP_URL, json=payload, headers=headers
            ) as resp:
                if resp.status in (400, 401, 403):
                    body = await resp.text()
                    raise AuthenticationError(
                        f"Cognito refresh failed ({resp.status}): {body}"
                    )
                if resp.status != 200:
                    body = await resp.text()
                    raise PerfectDraftApiError(resp.status, body)
                data = await resp.json(content_type=None)
        except aiohttp.ClientError as exc:
            raise PerfectDraftConnectionError(str(exc)) from exc

        result = data.get("AuthenticationResult", {})
        self._access_token = result.get("AccessToken", self._access_token)
        self._id_token = result.get("IdToken", self._id_token)
        # Cognito refresh doesn't return a new RefreshToken — the original stays valid

        _LOGGER.debug("Token refreshed via Cognito (expires in %ss)", result.get("ExpiresIn"))
        return result

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        """Make an authenticated API request with automatic 401 retry."""
        url = f"{self._base}{path}"
        headers = kwargs.pop("headers", {})
        headers["x-api-key"] = API_KEY
        if self._access_token:
            headers["x-access-token"] = self._access_token

        try:
            async with self._session.request(
                method, url, headers=headers, **kwargs
            ) as resp:
                if resp.status == 401:
                    _LOGGER.debug("Got 401, attempting Cognito token refresh")
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

    async def get_machine_active_keg(self, machine_id: str) -> dict[str, Any]:
        """GET active keg metadata for a machine.

        The default machine response omits kegActive. The documented
        perfectdraft_keg_active_read group adds the current keg resource and
        insertion timestamp without requiring product catalogue enumeration.
        """
        return await self._request(
            "GET",
            f"/api/perfectdraft_machines/{machine_id}",
            params={"groups[]": "perfectdraft_keg_active_read"},
        )

    async def update_machine_setting(
        self,
        setting_id: str,
        current_setting: dict[str, Any],
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace the machine setting while preserving existing fields.

        The API documents PUT rather than PATCH for settings. Keep the current
        setting values in the payload so changing one safe control does not
        accidentally clear unrelated settings, including pressure.
        """
        payload = {
            key: current_setting[key]
            for key in SETTING_WRITE_FIELDS
            if key in current_setting
        }
        payload.update(updates)
        return await self._request(
            "PUT",
            f"/api/perfectdraft_machine_settings/{setting_id}",
            json=payload,
        )

    async def set_product_favourite(
        self,
        profile: dict[str, Any],
        product_id: str,
    ) -> dict[str, Any]:
        """Mark a product as a favourite for the current customer."""
        customer = profile.get("@id")
        if not customer and profile.get("id") is not None:
            customer = f"/api/customers/{profile['id']}"
        if not customer:
            raise PerfectDraftApiError(400, "Customer IRI is unavailable")

        keg = f"/api/products/{product_id}"
        existing = _rating_for_keg(profile, keg)
        payload = {
            "customer": customer,
            "keg": keg,
            "favourite": True,
            "active": True,
        }
        if existing and isinstance(existing.get("rating"), int):
            payload["rating"] = existing["rating"]

        if existing and existing.get("id") is not None:
            return await self._request(
                "PUT",
                f"/api/customer_product_ratings/{existing['id']}",
                json=payload,
            )

        return await self._request(
            "POST",
            "/api/customer_product_ratings",
            json=payload,
        )


def _rating_for_keg(
    profile: dict[str, Any],
    keg_iri: str,
) -> dict[str, Any] | None:
    """Return the customer product rating for a keg IRI, if present."""
    for rating in profile.get("customerProductRatings") or []:
        if isinstance(rating, dict) and rating.get("keg") == keg_iri:
            return rating
    return None
