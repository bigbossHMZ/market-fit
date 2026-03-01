import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from apps.backend.clients.http import HttpClient


def _make_response(json_data=None, text=None, status_code=200):
    """Helper to build a mock httpx response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text if text is not None else ('{"ok": true}' if json_data is None else str(json_data))
    mock_response.json.return_value = json_data if json_data is not None else {"ok": True}
    mock_response.raise_for_status.return_value = None
    return mock_response


class TestHttpClientInit:
    def test_creates_async_client_when_none_injected(self):
        with patch("apps.backend.clients.http.httpx.AsyncClient") as mock_client_cls:
            HttpClient(base_url="https://example.com", retries=5, backoff_factor=2.0)
            mock_client_cls.assert_called_once()

    def test_uses_injected_client_as_is(self):
        with patch("apps.backend.clients.http.httpx.AsyncClient") as mock_client_cls:
            injected_client = AsyncMock()
            HttpClient(base_url="https://example.com", client=injected_client)
            mock_client_cls.assert_not_called()

    def test_strips_trailing_slash_from_base_url(self):
        client = HttpClient(base_url="https://example.com/", client=AsyncMock())
        assert client.base_url == "https://example.com"


class TestHttpClientRequest:
    def setup_method(self):
        self.mock_client = AsyncMock()
        # retries=0 keeps unit tests fast — no sleep loops for retryable status codes
        self.client = HttpClient(base_url="https://example.com", client=self.mock_client, retries=0)

    async def test_returns_parsed_json_on_success(self):
        self.mock_client.request.return_value = _make_response(json_data={"asin": "B001"})
        result = await self.client.get("/items/B001")
        assert result == {"asin": "B001"}

    async def test_returns_none_on_empty_body(self):
        self.mock_client.request.return_value = _make_response(text="")
        result = await self.client.get("/items/B001")
        assert result is None

    async def test_passes_correct_args_to_client(self):
        self.mock_client.request.return_value = _make_response()
        await self.client.get("/items/B001", params={"marketplace": "US"}, headers={"x-custom": "val"})
        self.mock_client.request.assert_called_once_with(
            "GET",
            "https://example.com/items/B001",
            auth=None,
            headers={"x-custom": "val"},
            params={"marketplace": "US"},
            json=None,
        )

    async def test_raises_and_logs_on_http_error(self):
        mock_response = _make_response(status_code=400)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400 Bad Request", request=MagicMock(), response=mock_response
        )
        self.mock_client.request.return_value = mock_response

        with patch("apps.backend.clients.http.logger") as mock_logger:
            with pytest.raises(httpx.HTTPStatusError):
                await self.client.get("/items/B001")
            mock_logger.error.assert_called_once()

    async def test_get_uses_get_method(self):
        self.mock_client.request.return_value = _make_response()
        await self.client.get("/path")
        assert self.mock_client.request.call_args.args[0] == "GET"

    async def test_post_uses_post_method(self):
        self.mock_client.request.return_value = _make_response()
        await self.client.post("/path", json={"key": "value"})
        assert self.mock_client.request.call_args.args[0] == "POST"
