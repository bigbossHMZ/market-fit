import pytest
from unittest.mock import MagicMock, patch
from requests.exceptions import HTTPError, RequestException
from apps.backend.clients.http import HttpClient


def _make_response(json_data=None, text=None, status_code=200):
    """Helper to build a mock response."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text if text is not None else ('{"ok": true}' if json_data is None else str(json_data))
    mock_response.json.return_value = json_data if json_data is not None else {"ok": True}
    mock_response.raise_for_status.return_value = None
    return mock_response


class TestHttpClientInit:
    def test_builds_retry_session_when_none_injected(self):
        with patch("apps.backend.clients.http._build_session") as mock_build:
            mock_build.return_value = MagicMock()
            HttpClient(base_url="https://example.com", retries=5, backoff_factor=2.0)
            mock_build.assert_called_once_with(5, 2.0)

    def test_uses_injected_session_as_is(self):
        with patch("apps.backend.clients.http._build_session") as mock_build:
            injected_session = MagicMock()
            HttpClient(base_url="https://example.com", session=injected_session)
            mock_build.assert_not_called()

    def test_strips_trailing_slash_from_base_url(self):
        client = HttpClient(base_url="https://example.com/", session=MagicMock())
        assert client.base_url == "https://example.com"


class TestHttpClientRequest:
    def setup_method(self):
        self.mock_session = MagicMock()
        self.client = HttpClient(base_url="https://example.com", session=self.mock_session)

    def test_returns_parsed_json_on_success(self):
        self.mock_session.request.return_value = _make_response(json_data={"asin": "B001"})
        result = self.client.get("/items/B001")
        assert result == {"asin": "B001"}

    def test_returns_none_on_empty_body(self):
        self.mock_session.request.return_value = _make_response(text="")
        result = self.client.get("/items/B001")
        assert result is None

    def test_passes_correct_args_to_session(self):
        self.mock_session.request.return_value = _make_response()
        self.client.get("/items/B001", params={"marketplace": "US"}, headers={"x-custom": "val"})
        self.mock_session.request.assert_called_once_with(
            method="GET",
            url="https://example.com/items/B001",
            auth=None,
            headers={"x-custom": "val"},
            params={"marketplace": "US"},
            json=None,
            timeout=self.client.timeout,
        )

    def test_raises_and_logs_on_http_error(self):
        mock_response = _make_response(status_code=500)
        mock_response.raise_for_status.side_effect = HTTPError(response=mock_response)
        self.mock_session.request.return_value = mock_response

        with patch("apps.backend.clients.http.logger") as mock_logger:
            with pytest.raises(RequestException):
                self.client.get("/items/B001")
            mock_logger.error.assert_called_once()

    def test_get_uses_get_method(self):
        self.mock_session.request.return_value = _make_response()
        self.client.get("/path")
        call_kwargs = self.mock_session.request.call_args
        assert call_kwargs.kwargs["method"] == "GET"

    def test_post_uses_post_method(self):
        self.mock_session.request.return_value = _make_response()
        self.client.post("/path", json={"key": "value"})
        call_kwargs = self.mock_session.request.call_args
        assert call_kwargs.kwargs["method"] == "POST"
