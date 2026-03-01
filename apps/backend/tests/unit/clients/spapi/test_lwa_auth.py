import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx

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


def _make_lwa_auth(config: LWAConfig | None = None) -> tuple[LWAAuth, AsyncMock]:
    """Builds an LWAAuth with an injected mock httpx.AsyncClient for testing."""
    mock_http = AsyncMock(spec=httpx.AsyncClient)
    auth = LWAAuth(config or _make_config(), client=mock_http)
    return auth, mock_http


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
    async def test_fetches_and_caches_token_on_first_call(self):
        auth, mock_http = _make_lwa_auth()
        mock_http.post.return_value = _make_token_response(access_token="new-token")

        token = await auth.get_access_token()

        assert token == "new-token"
        assert auth.token == "new-token"
        assert auth.expires_at is not None

    async def test_sends_correct_payload(self):
        config = _make_config()
        auth, mock_http = _make_lwa_auth(config)
        mock_http.post.return_value = _make_token_response()

        await auth.get_access_token()

        mock_http.post.assert_called_once_with(
            config.token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "refresh_token": config.refresh_token,
            },
        )

    async def test_returns_cached_token_when_not_expired(self):
        auth, mock_http = _make_lwa_auth()
        auth.token = "cached-token"
        auth.expires_at = _future(minutes=30)

        token = await auth.get_access_token()

        mock_http.post.assert_not_called()
        assert token == "cached-token"

    async def test_refreshes_when_expired(self):
        auth, mock_http = _make_lwa_auth()
        auth.token = "old-token"
        auth.expires_at = _future(minutes=0)
        mock_http.post.return_value = _make_token_response(access_token="new-token")

        token = await auth.get_access_token()

        assert token == "new-token"

    async def test_raises_spapi_auth_error_on_http_failure(self):
        auth, mock_http = _make_lwa_auth()
        mock_http.post.side_effect = httpx.ConnectError("connection error", request=MagicMock())

        with pytest.raises(SPAPIAuthError, match="LWA token fetch failed"):
            await auth.get_access_token()


class TestGetGrantlessToken:
    async def test_fetches_and_caches_token_per_scope(self):
        auth, mock_http = _make_lwa_auth()
        scope = "sellingpartnerapi::notifications"
        mock_http.post.return_value = _make_token_response(access_token="grantless-token")

        token = await auth.get_grantless_token(scope)

        assert token == "grantless-token"
        assert scope in auth._grantless_cache

    async def test_sends_correct_payload(self):
        config = _make_config()
        auth, mock_http = _make_lwa_auth(config)
        scope = "sellingpartnerapi::notifications"
        mock_http.post.return_value = _make_token_response()

        await auth.get_grantless_token(scope)

        mock_http.post.assert_called_once_with(
            config.token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "scope": scope,
            },
        )

    async def test_returns_cached_token_for_same_scope(self):
        auth, mock_http = _make_lwa_auth()
        scope = "sellingpartnerapi::notifications"
        auth._grantless_cache[scope] = ("cached-grantless-token", _future(minutes=30))

        token = await auth.get_grantless_token(scope)

        mock_http.post.assert_not_called()
        assert token == "cached-grantless-token"

    async def test_refreshes_expired_scope_token(self):
        auth, mock_http = _make_lwa_auth()
        scope = "sellingpartnerapi::notifications"
        auth._grantless_cache[scope] = ("old-token", _future(minutes=0))
        mock_http.post.return_value = _make_token_response(access_token="new-grantless-token")

        token = await auth.get_grantless_token(scope)

        assert token == "new-grantless-token"

    async def test_caches_different_scopes_independently(self):
        auth, mock_http = _make_lwa_auth()
        scope_a = "sellingpartnerapi::notifications"
        scope_b = "sellingpartnerapi::migration"
        mock_http.post.side_effect = [
            _make_token_response(access_token="token-a"),
            _make_token_response(access_token="token-b"),
        ]

        token_a = await auth.get_grantless_token(scope_a)
        token_b = await auth.get_grantless_token(scope_b)

        assert token_a == "token-a"
        assert token_b == "token-b"
        assert mock_http.post.call_count == 2

    async def test_raises_spapi_auth_error_on_http_failure(self):
        auth, mock_http = _make_lwa_auth()
        mock_http.post.side_effect = httpx.ConnectError("connection error", request=MagicMock())

        with pytest.raises(SPAPIAuthError, match="Grantless LWA token fetch failed"):
            await auth.get_grantless_token("sellingpartnerapi::notifications")
