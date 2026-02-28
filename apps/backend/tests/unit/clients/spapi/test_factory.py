import pytest
from unittest.mock import MagicMock, call, patch
from apps.backend.clients.spapi.base import SPAPIClient
from apps.backend.clients.spapi.config import LWAConfig, SPAPIConfig, StsConfig
from apps.backend.clients.spapi.factory import build_spapi_client, create_spapi_client


def _make_config() -> SPAPIConfig:
    return SPAPIConfig(
        stsconfig=StsConfig(
            role_arn="arn:aws:iam::123456789012:role/SPAPIRole",
            region="us-east-1",
            seller_id="SELLER123",
        ),
        lwaconfig=LWAConfig(
            token_url="https://api.amazon.com/auth/o2/token",
            client_id="client-id",
            client_secret="client-secret",
            refresh_token="refresh-token",
        ),
        endpoint_url="https://sellingpartnerapi-na.amazon.com",
    )


FACTORY_PATH = "apps.backend.clients.spapi.factory"


class TestBuildSpapiClient:
    def test_returns_spapi_client_instance(self):
        with patch(f"{FACTORY_PATH}.StsAuth"), \
             patch(f"{FACTORY_PATH}.LWAAuth"), \
             patch(f"{FACTORY_PATH}.SPAPIAuth"), \
             patch(f"{FACTORY_PATH}.HttpClient"):
            config = _make_config()
            result = build_spapi_client(config)
            assert isinstance(result, SPAPIClient)

    def test_wires_sts_auth_with_sts_config(self):
        config = _make_config()
        with patch(f"{FACTORY_PATH}.StsAuth") as mock_sts_auth, \
             patch(f"{FACTORY_PATH}.LWAAuth"), \
             patch(f"{FACTORY_PATH}.SPAPIAuth"), \
             patch(f"{FACTORY_PATH}.HttpClient"):
            build_spapi_client(config)
            mock_sts_auth.assert_called_once_with(config.stsconfig)

    def test_wires_lwa_auth_with_lwa_config(self):
        config = _make_config()
        with patch(f"{FACTORY_PATH}.StsAuth"), \
             patch(f"{FACTORY_PATH}.LWAAuth") as mock_lwa_auth, \
             patch(f"{FACTORY_PATH}.SPAPIAuth"), \
             patch(f"{FACTORY_PATH}.HttpClient"):
            build_spapi_client(config)
            mock_lwa_auth.assert_called_once_with(config.lwaconfig)

    def test_wires_spapi_auth_with_sts_and_lwa(self):
        config = _make_config()
        with patch(f"{FACTORY_PATH}.StsAuth") as mock_sts_auth, \
             patch(f"{FACTORY_PATH}.LWAAuth") as mock_lwa_auth, \
             patch(f"{FACTORY_PATH}.SPAPIAuth") as mock_spapi_auth, \
             patch(f"{FACTORY_PATH}.HttpClient"):
            build_spapi_client(config)
            mock_spapi_auth.assert_called_once_with(
                mock_sts_auth.return_value,
                mock_lwa_auth.return_value,
            )

    def test_wires_http_client_with_endpoint_and_transport_params(self):
        config = _make_config()
        with patch(f"{FACTORY_PATH}.StsAuth"), \
             patch(f"{FACTORY_PATH}.LWAAuth"), \
             patch(f"{FACTORY_PATH}.SPAPIAuth"), \
             patch(f"{FACTORY_PATH}.HttpClient") as mock_http:
            build_spapi_client(config, retries=5, backoff_factor=2.0, timeout=(3, 15))
            mock_http.assert_called_once_with(
                config.endpoint_url,
                retries=5,
                backoff_factor=2.0,
                timeout=(3, 15),
            )

    def test_uses_default_transport_params(self):
        config = _make_config()
        with patch(f"{FACTORY_PATH}.StsAuth"), \
             patch(f"{FACTORY_PATH}.LWAAuth"), \
             patch(f"{FACTORY_PATH}.SPAPIAuth"), \
             patch(f"{FACTORY_PATH}.HttpClient") as mock_http:
            build_spapi_client(config)
            mock_http.assert_called_once_with(
                config.endpoint_url,
                retries=3,
                backoff_factor=1.0,
                timeout=(5, 30),
            )


class TestCreateSpapiClient:
    def test_loads_config_from_env_and_builds_client(self):
        mock_config = _make_config()
        with patch(f"{FACTORY_PATH}.load_spapi_config", return_value=mock_config) as mock_load, \
             patch(f"{FACTORY_PATH}.build_spapi_client") as mock_build:
            create_spapi_client()
            mock_load.assert_called_once()
            mock_build.assert_called_once_with(
                mock_config,
                retries=3,
                backoff_factor=1.0,
                timeout=(5, 30),
            )

    def test_passes_transport_params_through(self):
        mock_config = _make_config()
        with patch(f"{FACTORY_PATH}.load_spapi_config", return_value=mock_config), \
             patch(f"{FACTORY_PATH}.build_spapi_client") as mock_build:
            create_spapi_client(retries=5, backoff_factor=2.0, timeout=(3, 15))
            mock_build.assert_called_once_with(
                mock_config,
                retries=5,
                backoff_factor=2.0,
                timeout=(3, 15),
            )

    def test_raises_if_env_var_missing(self):
        with patch(f"{FACTORY_PATH}.load_spapi_config", side_effect=ValueError("Missing: ROLE_ARN")):
            with pytest.raises(ValueError, match="ROLE_ARN"):
                create_spapi_client()
