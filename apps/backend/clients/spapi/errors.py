class SPAPIError(Exception):
    """Base class for all SP-API errors."""


class SPAPIAuthError(SPAPIError):
    """Raised when STS role assumption or LWA token fetch fails."""


class SPAPIThrottleError(SPAPIError):
    """Raised on 429 — request quota exceeded for the endpoint."""


class SPAPIClientError(SPAPIError):
    """Raised on 4xx responses (excluding 429)."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class SPAPIServerError(SPAPIError):
    """Raised on 5xx responses — transient server-side failures."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class SPAPINetworkError(SPAPIError):
    """Raised on timeouts or connection failures."""
