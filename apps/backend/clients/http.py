import logging
from typing import Any
from requests import Session, Response
from requests.auth import AuthBase
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, base_url: str, session: Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or Session()

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
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response: Response = self.session.request(
                method=method.upper(),
                url=url,
                auth=auth,
                headers=headers,
                params=params,
                json=json,
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
