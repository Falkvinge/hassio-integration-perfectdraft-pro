"""Exceptions for the PerfectDraft integration."""


class PerfectDraftError(Exception):
    """Base exception for PerfectDraft."""


_CREDENTIAL_ERROR_CODES = frozenset({"NotAuthorizedException", "UserNotFoundException"})
_TOKEN_ERROR_CODES = frozenset({"UserLambdaValidationException"})
_MAX_REASON_LENGTH = 200


class AuthenticationError(PerfectDraftError):
    """Raised when authentication fails (bad credentials, expired refresh token, reCAPTCHA rejection).

    ``code`` is the Cognito error type (e.g. ``NotAuthorizedException``) and
    ``reason`` its human-readable message, when the server supplied them.
    """

    def __init__(
        self, message: str, code: str | None = None, reason: str | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.reason = reason

    @property
    def kind(self) -> str:
        """Which input was rejected: ``credentials``, ``token`` or ``other``."""
        if self.code in _CREDENTIAL_ERROR_CODES:
            return "credentials"
        if self.code in _TOKEN_ERROR_CODES:
            return "token"
        return "other"

    @property
    def display_reason(self) -> str:
        """Server-supplied reason for the config flow, never empty."""
        text = (self.reason or self.code or "").strip().rstrip(".")
        return text[:_MAX_REASON_LENGTH] or "no reason given"


class PerfectDraftApiError(PerfectDraftError):
    """Raised on non-auth API errors (4xx/5xx)."""

    def __init__(self, status: int, message: str = "") -> None:
        super().__init__(f"API error {status}: {message}")
        self.status = status


class PerfectDraftConnectionError(PerfectDraftError):
    """Raised when the API is unreachable (network error, timeout)."""
