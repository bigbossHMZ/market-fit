import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx

from apps.backend.clients.spapi.base import SPAPIClient
from apps.backend.clients.spapi.errors import (
    SPAPIClientError,
    SPAPINetworkError,
    SPAPIServerError,
    SPAPIThrottleError,
)


class FakeSPAPIAuth:
    """Minimal async implementation of SPAPIAuthProtocol for testing."""

    def __init__(self):
        self._aws_auth = MagicMock()

    async def get_aws_auth(self):
        return self._aws_auth

    async def get_headers(self):
        return {"x-amz-access-token": "fake-token", "content-type": "application/json"}

    async def get_grantless_headers(self, scope: str):
        return {"x-amz-access-token": f"grantless-{scope}", "content-type": "application/json"}


def _make_http_error(status_code: int) -> httpx.HTTPStatusError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return httpx.HTTPStatusError("error", request=MagicMock(), response=mock_response)


class TestSPAPIClientRequests:
    def setup_method(self):
        self.auth = FakeSPAPIAuth()
        self.mock_http = AsyncMock()
        self.client = SPAPIClient(auth=self.auth, http=self.mock_http)

    async def test_get_calls_http_with_correct_args(self):
        self.mock_http.request.return_value = {"items": []}
        await self.client.get("/catalog/items", params={"marketplaceIds": "ATVPDKIKX0DER"})

        self.mock_http.request.assert_called_once_with(
            "GET",
            "/catalog/items",
            auth=self.auth._aws_auth,
            headers=await self.auth.get_headers(),
            params={"marketplaceIds": "ATVPDKIKX0DER"},
        )

    async def test_post_calls_http_with_correct_args(self):
        self.mock_http.request.return_value = {"orderId": "123"}
        await self.client.post("/orders", body={"key": "value"})

        self.mock_http.request.assert_called_once_with(
            "POST",
            "/orders",
            auth=self.auth._aws_auth,
            headers=await self.auth.get_headers(),
            json={"key": "value"},
        )

    async def test_get_grantless_calls_http_with_grantless_headers(self):
        scope = "sellingpartnerapi::notifications"
        self.mock_http.request.return_value = {"notifications": []}
        await self.client.get_grantless("/notifications", scope=scope)

        self.mock_http.request.assert_called_once_with(
            "GET",
            "/notifications",
            auth=self.auth._aws_auth,
            headers=await self.auth.get_grantless_headers(scope),
            params=None,
        )

    async def test_get_returns_http_response(self):
        self.mock_http.request.return_value = {"asin": "B001"}
        result = await self.client.get("/catalog/items/B001")
        assert result == {"asin": "B001"}


class TestSPAPIClientErrorTranslation:
    def setup_method(self):
        self.mock_http = AsyncMock()
        self.client = SPAPIClient(auth=FakeSPAPIAuth(), http=self.mock_http)

    async def test_timeout_raises_network_error(self):
        self.mock_http.request.side_effect = httpx.TimeoutException("timed out", request=MagicMock())
        with pytest.raises(SPAPINetworkError, match="timed out"):
            await self.client.get("/path")

    async def test_connection_error_raises_network_error(self):
        self.mock_http.request.side_effect = httpx.ConnectError("refused", request=MagicMock())
        with pytest.raises(SPAPINetworkError, match="Connection failed"):
            await self.client.get("/path")

    async def test_429_raises_throttle_error(self):
        self.mock_http.request.side_effect = _make_http_error(429)
        with pytest.raises(SPAPIThrottleError, match="Rate limit exceeded"):
            await self.client.get("/path")

    @pytest.mark.parametrize("status_code", [400, 403, 404])
    async def test_4xx_raises_client_error_with_status_code(self, status_code):
        self.mock_http.request.side_effect = _make_http_error(status_code)
        with pytest.raises(SPAPIClientError) as exc_info:
            await self.client.get("/path")
        assert exc_info.value.status_code == status_code

    @pytest.mark.parametrize("status_code", [500, 502, 503])
    async def test_5xx_raises_server_error_with_status_code(self, status_code):
        self.mock_http.request.side_effect = _make_http_error(status_code)
        with pytest.raises(SPAPIServerError) as exc_info:
            await self.client.get("/path")
        assert exc_info.value.status_code == status_code
