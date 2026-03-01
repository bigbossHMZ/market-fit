import asyncio
import logging
from datetime import datetime, timedelta, timezone

import boto3
import httpx
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials

from apps.backend.clients.spapi.config import LWAConfig, StsConfig
from apps.backend.clients.spapi.errors import SPAPIAuthError

logger = logging.getLogger(__name__)


class BotocoreAWS4Auth(httpx.Auth):
    """
    httpx.Auth implementation that signs requests with AWS Signature V4.

    Uses botocore (already a boto3 transitive dependency) for signing,
    replacing the requests-only requests_aws4auth library.
    """

    def __init__(self, access_key: str, secret_key: str, session_token: str, region: str, service: str = "execute-api"):
        self._credentials = Credentials(access_key, secret_key, session_token)
        self._region = region
        self._service = service

    def auth_flow(self, request: httpx.Request):
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
        )
        SigV4Auth(self._credentials, self._service, self._region).add_auth(aws_request)
        for key, value in aws_request.headers.items():
            request.headers[key] = value
        yield request


class StsAuth:
    def __init__(self, config: StsConfig):
        self.config = config
        self.credentials: dict = {}
        self._aws_auth: BotocoreAWS4Auth | None = None

    def _is_expired(self) -> bool:
        if not self.credentials:
            return True
        expiration: datetime = self.credentials["Expiration"]
        return datetime.now(timezone.utc) >= expiration - timedelta(minutes=5)

    def _do_assume_role(self) -> dict:
        """Synchronous boto3 STS call — runs in a thread executor to avoid blocking the event loop."""
        sts_client = boto3.client("sts", region_name=self.config.region)
        assumed_role_object = sts_client.assume_role(
            RoleArn=self.config.role_arn,
            RoleSessionName="AssumedRoleSession1",
            ExternalId=self.config.seller_id,
        )
        return assumed_role_object["Credentials"]

    async def _assume_role(self) -> dict:
        """Assumes the role and returns credentials. Refreshes if expired."""
        if self._is_expired():
            try:
                loop = asyncio.get_event_loop()
                self.credentials = await loop.run_in_executor(None, self._do_assume_role)
                self._aws_auth = None
            except Exception as e:
                logger.error("Error assuming role: %s", e)
                raise SPAPIAuthError(f"STS role assumption failed: {e}") from e
        return self.credentials

    async def get_aws_auth(self) -> BotocoreAWS4Auth:
        credentials = await self._assume_role()
        if self._aws_auth is None:
            self._aws_auth = BotocoreAWS4Auth(
                credentials["AccessKeyId"],
                credentials["SecretAccessKey"],
                credentials["SessionToken"],
                self.config.region,
            )
        return self._aws_auth


class LWAAuth:
    def __init__(self, config: LWAConfig, client: httpx.AsyncClient | None = None):
        self.config = config
        self.token: str = ""
        self.expires_at: datetime | None = None
        self._grantless_cache: dict[str, tuple[str, datetime]] = {}
        self._http = client or httpx.AsyncClient()

    def _is_expired(self) -> bool:
        if not self.token or not self.expires_at:
            return True
        return datetime.now(timezone.utc) >= self.expires_at - timedelta(minutes=1)

    async def get_access_token(self) -> str:
        """Returns a cached LWA access token, refreshing if expired."""
        if self._is_expired():
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
            }
            try:
                response = await self._http.post(self.config.token_url, data=data)
                response.raise_for_status()
                body = response.json()
                self.token = body["access_token"]
                expires_in = body.get("expires_in", 3600)
                self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            except httpx.HTTPError as e:
                logger.error("Error obtaining LWA token: %s", e)
                raise SPAPIAuthError(f"LWA token fetch failed: {e}") from e
        return self.token

    async def get_grantless_token(self, scope: str) -> str:
        """Returns a cached grantless LWA token for the given scope, refreshing if expired."""
        cached = self._grantless_cache.get(scope)
        if cached:
            token, expires_at = cached
            if datetime.now(timezone.utc) < expires_at - timedelta(minutes=1):
                return token
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": scope,
        }
        try:
            response = await self._http.post(self.config.token_url, data=data)
            response.raise_for_status()
            body = response.json()
            token = body["access_token"]
            expires_in = body.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            self._grantless_cache[scope] = (token, expires_at)
            return token
        except httpx.HTTPError as e:
            logger.error("Error obtaining grantless LWA token: %s", e)
            raise SPAPIAuthError(f"Grantless LWA token fetch failed: {e}") from e


class SPAPIAuth:
    def __init__(self, sts_auth: StsAuth, lwa_auth: LWAAuth):
        self.sts_auth = sts_auth
        self.lwa_auth = lwa_auth

    async def get_aws_auth(self) -> BotocoreAWS4Auth:
        return await self.sts_auth.get_aws_auth()

    async def get_headers(self) -> dict:
        return {
            "x-amz-access-token": await self.lwa_auth.get_access_token(),
            "content-type": "application/json",
        }

    async def get_grantless_headers(self, scope: str) -> dict:
        return {
            "x-amz-access-token": await self.lwa_auth.get_grantless_token(scope),
            "content-type": "application/json",
        }
