from dataclasses import dataclass

@dataclass(frozen=True)
class StsAuthConfig:
    role_arn: str
    region: str
    seller_id: str

@dataclass(frozen=True)
class LWAConfig:
    token_url: str
    client_id: str
    client_secret: str
    refresh_token: str

@dataclass(frozen=True)
class SPAPIConfig:
    endpoint_url: str
