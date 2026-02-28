import os
from dataclasses import dataclass

@dataclass(frozen=True)
class StsConfig:
    """ Configuration for STS authentication. """
    role_arn: str
    region: str
    seller_id: str

@dataclass(frozen=True)
class LWAConfig:
    """ Configuration for LWA authentication. """
    token_url: str
    client_id: str
    client_secret: str
    refresh_token: str

@dataclass(frozen=True)
class SPAPIConfig:
    """ Configuration for SPAPI client. """
    stsconfig: StsConfig
    lwaconfig: LWAConfig
    endpoint_url: str


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def load_spapi_config():
    """ Load SPAPI configuration from environment variables. """
    sts_config = StsConfig(
        role_arn=_require_env("ROLE_ARN"),
        region=_require_env("REGION"),
        seller_id=_require_env("SELLER_ID")
    )
    lwa_config = LWAConfig(
        token_url=_require_env("LWA_TOKEN_URL"),
        client_id=_require_env("LWA_CLIENT_ID"),
        client_secret=_require_env("LWA_CLIENT_SECRET"),
        refresh_token=_require_env("LWA_REFRESH_TOKEN")
    )
    sp_api_config = SPAPIConfig(
        stsconfig=sts_config,
        lwaconfig=lwa_config,
        endpoint_url=_require_env("SP_API_ENDPOINT_URL")
    )
    return sp_api_config
