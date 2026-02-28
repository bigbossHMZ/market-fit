
import logging
import requests
from datetime import datetime, timedelta, timezone
from requests_aws4auth import AWS4Auth
import boto3
from apps.backend.clients.spapi.config import LWAConfig, StsConfig
from apps.backend.clients.spapi.errors import SPAPIAuthError

logger = logging.getLogger(__name__)

class StsAuth():
    def __init__(self, config: StsConfig):
        self.config = config
        self.credentials: dict = {}
        self._aws_auth: AWS4Auth | None = None

    def _is_expired(self) -> bool:
        if not self.credentials:
            return True
        expiration: datetime = self.credentials['Expiration']
        return datetime.now(timezone.utc) >= expiration - timedelta(minutes=5)

    def _assume_role(self) -> dict:
        """ Assumes the role and returns the credentials. Refreshes if expired. """
        if self._is_expired():
            sts_client = boto3.client('sts', region_name=self.config.region)
            try:
                assumed_role_object = sts_client.assume_role(
                    RoleArn=self.config.role_arn,
                    RoleSessionName="AssumedRoleSession1",
                    ExternalId=self.config.seller_id
                )
                self.credentials = assumed_role_object['Credentials']
                self._aws_auth = None
            except Exception as e:
                logger.error(f"Error assuming role: {e}")
                raise SPAPIAuthError(f"STS role assumption failed: {e}") from e
        return self.credentials

    def get_aws_auth(self) -> AWS4Auth:
        credentials = self._assume_role()
        if self._aws_auth is None:
            self._aws_auth = AWS4Auth(
                credentials['AccessKeyId'],
                credentials['SecretAccessKey'],
                self.config.region,
                'execute-api',
                session_token=credentials['SessionToken']
            )
        return self._aws_auth


class LWAAuth:
    def __init__(self, config: LWAConfig):
        self.config = config
        self.token: str = ""
        self.expires_at: datetime | None = None
        self._grantless_cache: dict[str, tuple[str, datetime]] = {}

    def _is_expired(self) -> bool:
        if not self.token or not self.expires_at:
            return True
        return datetime.now(timezone.utc) >= self.expires_at - timedelta(minutes=1)

    def get_access_token(self) -> str:
        """ Returns a cached LWA access token, refreshing if expired. """
        if self._is_expired():
            data = {
                "grant_type": "refresh_token",
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
            }
            try:
                response = requests.post(self.config.token_url, data=data)
                response.raise_for_status()
                body = response.json()
                self.token = body["access_token"]
                expires_in = body.get("expires_in", 3600)
                self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            except requests.RequestException as e:
                logger.error(f"Error obtaining LWA token: {e}")
                raise SPAPIAuthError(f"LWA token fetch failed: {e}") from e
        return self.token

    def get_grantless_token(self, scope: str) -> str:
        """ Returns a cached grantless LWA token for the given scope, refreshing if expired. """
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
            response = requests.post(self.config.token_url, data=data)
            response.raise_for_status()
            body = response.json()
            token = body["access_token"]
            expires_in = body.get("expires_in", 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            self._grantless_cache[scope] = (token, expires_at)
            return token
        except requests.RequestException as e:
            logger.error(f"Error obtaining grantless LWA token: {e}")
            raise SPAPIAuthError(f"Grantless LWA token fetch failed: {e}") from e


class SPAPIAuth:
    def __init__(self, sts_auth: StsAuth, lwa_auth: LWAAuth):
        self.sts_auth = sts_auth
        self.lwa_auth = lwa_auth

    def get_aws_auth(self) -> AWS4Auth:
        return self.sts_auth.get_aws_auth()

    def get_headers(self) -> dict:
        return {
            "x-amz-access-token": self.lwa_auth.get_access_token(),
            "content-type": "application/json",
        }

    def get_grantless_headers(self, scope: str) -> dict:
        return {
            "x-amz-access-token": self.lwa_auth.get_grantless_token(scope),
            "content-type": "application/json",
        }
