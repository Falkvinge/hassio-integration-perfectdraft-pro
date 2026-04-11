"""Server-side reCAPTCHA v3 token generation for PerfectDraft.

Uses the reCAPTCHA anchor/reload HTTP flow to obtain a token without
requiring a browser on an allowed domain. This works because the
PerfectDraft API uses an Android reCAPTCHA key, and the anchor endpoint
does not enforce domain validation the same way the JS widget does.

If this approach stops working, the fallback is the browser-based
external step flow.
"""
from __future__ import annotations

import logging
import re

import aiohttp

from .const import RECAPTCHA_SITE_KEY

_LOGGER = logging.getLogger(__name__)

ANCHOR_URL = (
    "https://www.google.com/recaptcha/api2/anchor"
    f"?ar=1&k={RECAPTCHA_SITE_KEY}&co=aHR0cHM6Ly9wZXJmZWN0ZHJhZnQuY29t"
    "&hl=en&v=pCoGBhjs9s8EhFOHJFe8BCfw&size=invisible&cb=1"
)

RELOAD_URL = "https://www.google.com/recaptcha/api2/reload"

_TOKEN_RE = re.compile(r'"recaptcha-token"\s+value="([^"]+)"')
_RRESP_RE = re.compile(r'"rresp"\s*,\s*"([^"]+)"')


async def async_generate_recaptcha_token(
    session: aiohttp.ClientSession,
) -> str | None:
    """Attempt to generate a reCAPTCHA token server-side.

    Returns the token string, or None if generation fails.
    """
    try:
        async with session.get(ANCHOR_URL) as resp:
            if resp.status != 200:
                _LOGGER.debug("Anchor request failed: %s", resp.status)
                return None
            html = await resp.text()

        match = _TOKEN_RE.search(html)
        if not match:
            _LOGGER.debug("Could not find recaptcha-token in anchor response")
            return None

        anchor_token = match.group(1)

        payload = {
            "v": "pCoGBhjs9s8EhFOHJFe8BCfw",
            "reason": "q",
            "c": anchor_token,
            "k": RECAPTCHA_SITE_KEY,
            "co": "aHR0cHM6Ly9wZXJmZWN0ZHJhZnQuY29t",
            "hl": "en",
            "size": "invisible",
        }

        async with session.post(RELOAD_URL, data=payload) as resp:
            if resp.status != 200:
                _LOGGER.debug("Reload request failed: %s", resp.status)
                return None
            body = await resp.text()

        match = _RRESP_RE.search(body)
        if not match:
            _LOGGER.debug("Could not find rresp token in reload response")
            return None

        token = match.group(1)
        _LOGGER.debug("Generated reCAPTCHA token server-side (length=%d)", len(token))
        return token

    except aiohttp.ClientError as exc:
        _LOGGER.debug("reCAPTCHA token generation failed: %s", exc)
        return None
    except Exception:
        _LOGGER.exception("Unexpected error generating reCAPTCHA token")
        return None
