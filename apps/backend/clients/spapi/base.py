import logging
from typing import Any
from apps.backend.clients.http import HttpClient
from apps.backend.clients.spapi.auth import SPAPIAuth

logger = logging.getLogger(__name__)


class SPAPIClient:
    def __init__(self, auth: SPAPIAuth, http: HttpClient):
        self.auth = auth
        self.http = http

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.http.get(
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            params=params,
        )

    def post(self, path: str, body: Any = None) -> Any:
        return self.http.post(
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_headers(),
            json=body,
        )

    def get_grantless(self, path: str, scope: str, params: dict | None = None) -> Any:
        return self.http.get(
            path,
            auth=self.auth.get_aws_auth(),
            headers=self.auth.get_grantless_headers(scope),
            params=params,
        )
