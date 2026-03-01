import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Status codes that warrant a retry. 429 is throttling, 5xx are transient server errors.
_RETRY_ON = {429, 500, 502, 503, 504}


class HttpClient:
    """
    Generic async HTTP client with built-in retry, backoff, and timeout.

    Designed to be injected into API-specific clients (SPAPIClient,
    KeepaClient, etc.) so that transport concerns are handled in one place.

    Args:
        base_url: Base URL prepended to all request paths.
        client: Optional pre-configured httpx.AsyncClient. If provided, timeout
                configuration is skipped — the caller is responsible. Useful for tests.
        retries: Maximum number of retry attempts on throttling or server errors (default: 3).
        backoff_factor: Multiplier for exponential backoff between retries (default: 1.0).
                        Formula: sleep = backoff_factor * 2^attempt. With 1.0: 1s, 2s, 4s.
        timeout: (connect_timeout, read_timeout) in seconds (default: (5, 30)).
    """

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: tuple[int, int] = (5, 30),
    ):
        self.base_url = base_url.rstrip("/")
        self._retries = retries
        self._backoff_factor = backoff_factor
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=timeout[0],
                read=timeout[1],
                write=timeout[1],
                pool=timeout[1]
            )
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        auth: httpx.Auth | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        """
        Executes an async HTTP request and returns the parsed JSON response.

        Retries on 429 and 5xx responses with exponential backoff, honouring
        any Retry-After header returned by the server.
        Returns None if the response body is empty.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(self._retries + 1):
            try:
                response = await self._client.request(
                    method.upper(),
                    url,
                    auth=auth,
                    headers=headers,
                    params=params,
                    json=json,
                )
                if response.status_code in _RETRY_ON and attempt < self._retries:
                    retry_after = response.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else self._backoff_factor * (2 ** attempt)
                    logger.warning(
                        "Retrying %s %s after %.1fs (attempt %d/%d)",
                        method.upper(), url, wait, attempt + 1, self._retries,
                    )
                    await asyncio.sleep(wait)
                    continue
                response.raise_for_status()
                return response.json() if response.text else None
            except httpx.HTTPError as e:
                logger.error("HTTP %s %s failed: %s", method.upper(), url, e)
                raise

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Any:
        return await self.request("POST", path, **kwargs)

    async def aclose(self) -> None:
        await self._client.aclose()
