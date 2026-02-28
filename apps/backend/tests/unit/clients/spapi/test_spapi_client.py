import pytest
from unittest.mock import MagicMock
from requests.exceptions import ConnectionError, HTTPError, Timeout
from apps.backend.clients.spapi.base import SPAPIClient
from apps.backend.clients.spapi.errors import (
    SPAPIClientError,
    SPAPINetworkError,
    SPAPIServerError,
    SPAPIThrottleError,
)


class FakeSPAPIAuth:
    """Minimal implementation of SPAPIAuthProtocol for testing."""

    def __init__(self):
        self._aws_auth = MagicMock()

    def get_aws_auth(self):
        return self._aws_auth

    def get_headers(self):
        return {"x-amz-access-token": "fake-token", "content-type": "application/json"}

    def get_grantless_headers(self, scope: str):
        return {"x-amz-access-token": f"grantless-{scope}", "content-type": "application/json"}


def _make_http_error(status_code: int) -> HTTPError:
    mock_response = MagicMock()
    mock_response.status_code = status_code
    return HTTPError(response=mock_response)


class TestSPAPIClientRequests:
    def setup_method(self):
        self.auth = FakeSPAPIAuth()
        self.mock_http = MagicMock()
        self.client = SPAPIClient(auth=self.auth, http=self.mock_http)

    def test_get_calls_http_with_correct_args(self):
        self.mock_http.request.return_value = {"items": []}
        self.client.get("/catalog/items", params={"marketplaceIds": "ATVPDKIKX0DER"})

        self.mock_http.request.assert_called_once_with(
            "GET",
            "/catalog/items",
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            params={"marketplaceIds": "ATVPDKIKX0DER"},
        )

    def test_post_calls_http_with_correct_args(self):
        self.mock_http.request.return_value = {"orderId": "123"}
        self.client.post("/orders", body={"key": "value"})

        self.mock_http.request.assert_called_once_with(
            "POST",
            "/orders",
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            json={"key": "value"},
        )

    def test_get_grantless_calls_http_with_grantless_headers(self):
        scope = "sellingpartnerapi::notifications"
        self.mock_http.request.return_value = {"notifications": []}
        self.client.get_grantless("/notifications", scope=scope)

        self.mock_http.request.assert_called_once_with(
            "GET",
            "/notifications",
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_grantless_headers(scope),
            params=None,
        )

    def test_get_returns_http_response(self):
        self.mock_http.request.return_value = {"asin": "B001"}
        result = self.client.get("/catalog/items/B001")
        assert result == {"asin": "B001"}


class TestSPAPIClientErrorTranslation:
    def setup_method(self):
        self.mock_http = MagicMock()
        self.client = SPAPIClient(auth=FakeSPAPIAuth(), http=self.mock_http)

    def test_timeout_raises_network_error(self):
        self.mock_http.request.side_effect = Timeout()
        with pytest.raises(SPAPINetworkError, match="timed out"):
            self.client.get("/path")

    def test_connection_error_raises_network_error(self):
        self.mock_http.request.side_effect = ConnectionError()
        with pytest.raises(SPAPINetworkError, match="Connection failed"):
            self.client.get("/path")

    def test_429_raises_throttle_error(self):
        self.mock_http.request.side_effect = _make_http_error(429)
        with pytest.raises(SPAPIThrottleError, match="Rate limit exceeded"):
            self.client.get("/path")

    @pytest.mark.parametrize("status_code", [400, 403, 404])
    def test_4xx_raises_client_error_with_status_code(self, status_code):
        self.mock_http.request.side_effect = _make_http_error(status_code)
        with pytest.raises(SPAPIClientError) as exc_info:
            self.client.get("/path")
        assert exc_info.value.status_code == status_code

    @pytest.mark.parametrize("status_code", [500, 502, 503])
    def test_5xx_raises_server_error_with_status_code(self, status_code):
        self.mock_http.request.side_effect = _make_http_error(status_code)
        with pytest.raises(SPAPIServerError) as exc_info:
            self.client.get("/path")
        assert exc_info.value.status_code == status_code
