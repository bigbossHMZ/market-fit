import logging
from typing import Any
from requests import Session, Response
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase
from requests.exceptions import RequestException
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Status codes that warrant a retry. 429 is throttling, 5xx are transient server errors.
_RETRY_ON = (429, 500, 502, 503, 504)


def _build_session(retries: int, backoff_factor: float) -> Session:
    """
    Builds a requests Session pre-configured with retry and backoff.

    Retry formula: sleep = backoff_factor * 2^(attempt - 1)
    With backoff_factor=1.0: waits 1s, 2s, 4s between attempts.

    respect_retry_after_header=True makes urllib3 honor the Retry-After
    header returned by APIs on 429 responses instead of using the backoff formula.

    Only mounted on https:// — http:// calls are not retried.
    """
    session = Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=_RETRY_ON,
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


class HttpClient:
    """
    Generic HTTP client with built-in retry, backoff, and timeout.

    Designed to be injected into API-specific clients (SPAPIClient,
    KeepaClient, etc.) so that transport concerns are handled in one place.

    Args:
        base_url: Base URL prepended to all request paths.
        session: Optional pre-configured requests.Session. If provided, retry
                configuration is skipped — the caller is responsible. Useful for tests.
        retries: Maximum number of retry attempts on failure (default: 3).
        backoff_factor: Multiplier for exponential backoff between retries
                        (default: 1.0).
        timeout: (connect_timeout, read_timeout) in seconds. Connect timeout
                caps how longto wait for a TCP connection. Read timeout caps
                how long to wait for the server to respond. Kept separate
                because slow APIs can have fast connectsbut slow responses
                (default: (5, 30)).
    """

    def __init__(
        self,
        base_url: str,
        session: Session | None = None,
        retries: int = 3,
        backoff_factor: float = 1.0,
        timeout: tuple[int, int] = (5, 30),
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session if session is not None else _build_session(retries, backoff_factor)

    def request(
        self,
        method: str,
        path: str,
        *,
        auth: AuthBase | None = None,
        headers: dict | None = None,
        params: dict | None = None,
        json: Any = None,
    ) -> Any:
        """
        Executes an HTTP request and returns the parsed JSON response.

        Raises RequestException on HTTP errors or network failures.
        Returns None if the response body is empty.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response: Response = self.session.request(
                method=method.upper(),
                url=url,
                auth=auth,
                headers=headers,
                params=params,
                json=json,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json() if response.text else None
        except RequestException as e:
            logger.error("HTTP %s %s failed: %s", method.upper(), url, e)
            raise

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)
