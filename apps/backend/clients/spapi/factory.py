from apps.backend.clients.http import HttpClient
from apps.backend.clients.spapi.auth import LWAAuth, SPAPIAuth, StsAuth
from apps.backend.clients.spapi.base import SPAPIClient
from apps.backend.clients.spapi.config import SPAPIConfig, load_spapi_config


def build_spapi_client(
    config: SPAPIConfig,
    retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: tuple[int, int] = (5, 30),
) -> SPAPIClient:
    """
    Wires all SP-API dependencies together and returns a ready-to-use SPAPIClient.

    Accepts optional HttpClient parameters so callers can tune transport behaviour
    (e.g. stricter timeouts or more retries) without touching internal wiring.
    """
    sts_auth = StsAuth(config.stsconfig)
    lwa_auth = LWAAuth(config.lwaconfig)
    auth = SPAPIAuth(sts_auth, lwa_auth)
    http = HttpClient(config.endpoint_url, retries=retries, backoff_factor=backoff_factor, timeout=timeout)
    return SPAPIClient(auth, http)


def create_spapi_client(
    retries: int = 3,
    backoff_factor: float = 1.0,
    timeout: tuple[int, int] = (5, 30),
) -> SPAPIClient:
    """
    Convenience function that loads config from environment variables
    and returns a ready-to-use SPAPIClient.

    Raises ValueError if any required environment variable is missing.
    """
    config = load_spapi_config()
    return build_spapi_client(config, retries=retries, backoff_factor=backoff_factor, timeout=timeout)
