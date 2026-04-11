"""Exceptions for the PerfectDraft integration."""


class PerfectDraftError(Exception):
    """Base exception for PerfectDraft."""


class AuthenticationError(PerfectDraftError):
    """Raised when authentication fails (bad credentials, expired refresh token, reCAPTCHA rejection)."""


class PerfectDraftApiError(PerfectDraftError):
    """Raised on non-auth API errors (4xx/5xx)."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"API error {status}: {message}")
        self.status = status


class PerfectDraftConnectionError(PerfectDraftError):
    """Raised when the API is unreachable (network error, timeout)."""
