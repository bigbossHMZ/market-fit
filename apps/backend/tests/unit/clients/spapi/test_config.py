import pytest
from unittest.mock import patch
from apps.backend.clients.spapi.config import (
    SPAPIConfig,
    StsConfig,
    LWAConfig,
    _require_env,
    load_spapi_config,
)

VALID_ENV = {
    "ROLE_ARN": "arn:aws:iam::123456789012:role/SPAPIRole",
    "REGION": "us-east-1",
    "SELLER_ID": "SELLER123",
    "LWA_TOKEN_URL": "https://api.amazon.com/auth/o2/token",
    "LWA_CLIENT_ID": "client-id",
    "LWA_CLIENT_SECRET": "client-secret",
    "LWA_REFRESH_TOKEN": "refresh-token",
    "SP_API_ENDPOINT_URL": "https://sellingpartnerapi-na.amazon.com",
}


class TestRequireEnv:
    def test_returns_value_when_set(self):
        with patch.dict("os.environ", {"MY_VAR": "hello"}):
            assert _require_env("MY_VAR") == "hello"

    def test_raises_when_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="MY_VAR"):
                _require_env("MY_VAR")


class TestLoadSpapiConfig:
    def test_builds_correct_config(self):
        with patch.dict("os.environ", VALID_ENV):
            config = load_spapi_config()

        assert isinstance(config, SPAPIConfig)
        assert isinstance(config.stsconfig, StsConfig)
        assert isinstance(config.lwaconfig, LWAConfig)

        assert config.stsconfig.role_arn == VALID_ENV["ROLE_ARN"]
        assert config.stsconfig.region == VALID_ENV["REGION"]
        assert config.stsconfig.seller_id == VALID_ENV["SELLER_ID"]

        assert config.lwaconfig.token_url == VALID_ENV["LWA_TOKEN_URL"]
        assert config.lwaconfig.client_id == VALID_ENV["LWA_CLIENT_ID"]
        assert config.lwaconfig.client_secret == VALID_ENV["LWA_CLIENT_SECRET"]
        assert config.lwaconfig.refresh_token == VALID_ENV["LWA_REFRESH_TOKEN"]

        assert config.endpoint_url == VALID_ENV["SP_API_ENDPOINT_URL"]

    @pytest.mark.parametrize("missing_key", VALID_ENV.keys())
    def test_raises_when_any_var_is_missing(self, missing_key):
        env = {k: v for k, v in VALID_ENV.items() if k != missing_key}
        with patch.dict("os.environ", env, clear=True):
            with pytest.raises(ValueError, match=missing_key):
                load_spapi_config()
