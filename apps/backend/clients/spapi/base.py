import logging
from typing import Any, Protocol
from requests import Timeout, ConnectionError, HTTPError
from requests_aws4auth import AWS4Auth
from apps.backend.clients.http import HttpClient
from apps.backend.clients.spapi.errors import (
    SPAPIThrottleError,
    SPAPIClientError,
    SPAPIServerError,
    SPAPINetworkError,
)

logger = logging.getLogger(__name__)


class SPAPIAuthProtocol(Protocol):
    def get_aws_auth(self) -> AWS4Auth: ...
    def get_headers(self) -> dict: ...
    def get_grantless_headers(self, scope: str) -> dict: ...


class SPAPIClient:
    def __init__(self, auth: SPAPIAuthProtocol, http: HttpClient):
        self.auth = auth
        self.http = http

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            return self.http.request(method, path, **kwargs)
        except Timeout as e:
            raise SPAPINetworkError(f"Request timed out: {path}") from e
        except ConnectionError as e:
            raise SPAPINetworkError(f"Connection failed: {path}") from e
        except HTTPError as e:
            status = e.response.status_code
            if status == 429:
                raise SPAPIThrottleError(f"Rate limit exceeded: {path}") from e
            elif 400 <= status < 500:
                raise SPAPIClientError(f"Client error {status}: {path}", status) from e
            elif 500 <= status < 600:
                raise SPAPIServerError(f"Server error {status}: {path}", status) from e
            raise

    def get(self, path: str, params: dict | None = None) -> Any:
        return self._request(
            "GET",
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            params=params,
        )

    def post(self, path: str, body: Any = None) -> Any:
        return self._request(
            "POST",
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            json=body,
        )

    def get_grantless(self, path: str, scope: str, params: dict | None = None) -> Any:
        return self._request(
            "GET",
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_grantless_headers(scope),
            params=params,
        )
