import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from requests.exceptions import RequestException
from apps.backend.clients.spapi.auth import LWAAuth
from apps.backend.clients.spapi.config import LWAConfig
from apps.backend.clients.spapi.errors import SPAPIAuthError


def _make_config() -> LWAConfig:
    return LWAConfig(
        token_url="https://api.amazon.com/auth/o2/token",
        client_id="client-id",
        client_secret="client-secret",
        refresh_token="refresh-token",
    )


def _make_token_response(access_token: str = "access-token", expires_in: int = 3600) -> MagicMock:
    """Builds a mock HTTP response for a successful LWA token fetch."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": access_token, "expires_in": expires_in}
    mock_response.raise_for_status.return_value = None
    return mock_response


def _future(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


class TestIsExpired:
    def test_returns_true_when_token_is_empty(self):
        auth = LWAAuth(_make_config())
        assert auth._is_expired() is True

    def test_returns_true_when_expiry_within_1_minute(self):
        auth = LWAAuth(_make_config())
        auth.token = "some-token"
        auth.expires_at = _future(minutes=0)
        assert auth._is_expired() is True

    def test_returns_false_when_token_is_fresh(self):
        auth = LWAAuth(_make_config())
        auth.token = "some-token"
        auth.expires_at = _future(minutes=30)
        assert auth._is_expired() is False


class TestGetAccessToken:
    def test_fetches_and_caches_token_on_first_call(self):
        auth = LWAAuth(_make_config())

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response(access_token="new-token")
            token = auth.get_access_token()

        assert token == "new-token"
        assert auth.token == "new-token"
        assert auth.expires_at is not None

    def test_sends_correct_payload(self):
        config = _make_config()
        auth = LWAAuth(config)

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response()
            auth.get_access_token()

        mock_post.assert_called_once_with(
            config.token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": config.refresh_token,
            },
        )

    def test_returns_cached_token_when_not_expired(self):
        auth = LWAAuth(_make_config())
        auth.token = "cached-token"
        auth.expires_at = _future(minutes=30)

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            token = auth.get_access_token()
            mock_post.assert_not_called()

        assert token == "cached-token"

    def test_refreshes_when_expired(self):
        auth = LWAAuth(_make_config())
        auth.token = "old-token"
        auth.expires_at = _future(minutes=0)

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response(access_token="new-token")
            token = auth.get_access_token()

        assert token == "new-token"

    def test_raises_spapi_auth_error_on_http_failure(self):
        auth = LWAAuth(_make_config())

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.side_effect = RequestException("connection error")

            with pytest.raises(SPAPIAuthError, match="LWA token fetch failed"):
                auth.get_access_token()


class TestGetGrantlessToken:
    def test_fetches_and_caches_token_per_scope(self):
        auth = LWAAuth(_make_config())
        scope = "sellingpartnerapi::notifications"

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response(access_token="grantless-token")
            token = auth.get_grantless_token(scope)

        assert token == "grantless-token"
        assert scope in auth._grantless_cache

    def test_sends_correct_payload(self):
        config = _make_config()
        auth = LWAAuth(config)
        scope = "sellingpartnerapi::notifications"

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response()
            auth.get_grantless_token(scope)

        mock_post.assert_called_once_with(
            config.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "scope": scope,
            },
        )

    def test_returns_cached_token_for_same_scope(self):
        auth = LWAAuth(_make_config())
        scope = "sellingpartnerapi::notifications"
        auth._grantless_cache[scope] = ("cached-grantless-token", _future(minutes=30))

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            token = auth.get_grantless_token(scope)
            mock_post.assert_not_called()

        assert token == "cached-grantless-token"

    def test_refreshes_expired_scope_token(self):
        auth = LWAAuth(_make_config())
        scope = "sellingpartnerapi::notifications"
        auth._grantless_cache[scope] = ("old-token", _future(minutes=0))

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.return_value = _make_token_response(access_token="new-grantless-token")
            token = auth.get_grantless_token(scope)

        assert token == "new-grantless-token"

    def test_caches_different_scopes_independently(self):
        auth = LWAAuth(_make_config())
        scope_a = "sellingpartnerapi::notifications"
        scope_b = "sellingpartnerapi::migration"

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.side_effect = [
                _make_token_response(access_token="token-a"),
                _make_token_response(access_token="token-b"),
            ]
            token_a = auth.get_grantless_token(scope_a)
            token_b = auth.get_grantless_token(scope_b)

        assert token_a == "token-a"
        assert token_b == "token-b"
        assert mock_post.call_count == 2

    def test_raises_spapi_auth_error_on_http_failure(self):
        auth = LWAAuth(_make_config())

        with patch("apps.backend.clients.spapi.auth.requests.post") as mock_post:
            mock_post.side_effect = RequestException("connection error")

            with pytest.raises(SPAPIAuthError, match="Grantless LWA token fetch failed"):
                auth.get_grantless_token("sellingpartnerapi::notifications")
