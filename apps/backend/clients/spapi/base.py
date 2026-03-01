import logging
from typing import Any, Protocol

import httpx

from apps.backend.clients.http import HttpClient
from apps.backend.clients.spapi.errors import (
    SPAPIClientError,
    SPAPINetworkError,
    SPAPIServerError,
    SPAPIThrottleError,
)

logger = logging.getLogger(__name__)


class SPAPIAuthProtocol(Protocol):
    async def get_aws_auth(self) -> httpx.Auth: ...
    async def get_headers(self) -> dict: ...
    async def get_grantless_headers(self, scope: str) -> dict: ...


class SPAPIClient:
    def __init__(self, auth: SPAPIAuthProtocol, http: HttpClient):
        self.auth = auth
        self.http = http

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            return await self.http.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            raise SPAPINetworkError(f"Request timed out: {path}") from e
        except httpx.ConnectError as e:
            raise SPAPINetworkError(f"Connection failed: {path}") from e
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429:
                raise SPAPIThrottleError(f"Rate limit exceeded: {path}") from e
            elif 400 <= status < 500:
                raise SPAPIClientError(f"Client error {status}: {path}", status) from e
            elif 500 <= status < 600:
                raise SPAPIServerError(f"Server error {status}: {path}", status) from e
            raise

    async def get(self, path: str, params: dict | None = None) -> Any:
        return await self._request(
            "GET",
            path,
            auth=await self.auth.get_aws_auth(),
            headers=await self.auth.get_headers(),
            params=params,
        )

    async def post(self, path: str, body: Any = None) -> Any:
        return await self._request(
            "POST",
            path,
            auth=await self.auth.get_aws_auth(),
            headers=await self.auth.get_headers(),
            json=body,
        )

    async def get_grantless(self, path: str, scope: str, params: dict | None = None) -> Any:
        return await self._request(
            "GET",
            path,
            auth=await self.auth.get_aws_auth(),
            headers=await self.auth.get_grantless_headers(scope),
            params=params,
        )
