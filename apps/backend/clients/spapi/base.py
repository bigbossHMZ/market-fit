import boto3
import requests
from requests_aws4auth import AWS4Auth
import logging
from botocore.exceptions import ClientError
from config import *
from requests.exceptions import RequestException
from urllib.parse import urlencode, urljoin
from datetime import datetime, timezone, timedelta

# this API client should be in backend FastApi, fast api should forward the needed data to the worker
# However since I will be working a lot with SP_API, it should be a package on its own that I can import in the FASTAPI backend and in any script for which I need to interact with SP_API.

# I have to secure the access to the tokens.

# TODO:
# - Create a .env to store refresh tokens
# - Design the connector to acceept a TokenProvider to retrive those tokens.
# - Add actual Logging, make sure logged information is not sensitive.
# - Add retry + backoff + jitter. Retry on 429, 500-599, connection reset
#   and timeouts. Exponential backoff + jitter.
# - Enforce timeouts
# - Cache sts credentials with expiry handling same as LWA Token.
# - Use requests.Session() instead of calling get/post directly.
# - This file should handle signing, tokens, request, retry and timeouts.
# - Actual api calls will be in xxx_api.py.
# - xxx_api calls should return domain models.
# - Add typed errors :
#   SpAPIAuthError, SpApiThrottleError, SpApiServerError,
#   SpApiClientError, SpApiNetworkError.
# - Standardise handling of tokens (lwa vs lwa grantless)



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleSPAPI:
    def __init__(self,
                sts_auth_config: StsAuthConfig,
                lwa_config: LWAConfig,
                sp_api_config: SPAPIConfig):

        self.sts_auth_config = sts_auth_config
        self.lwa_config = lwa_config
        self.sp_api_config = sp_api_config

        self.session = boto3.Session()
        self.lwa_token_expires_at = None
        self.credentials = None
        self.auth = None
        self.lwa_token = None

    # auth
    def assume_role(self):
        """ Assumes the role and caches the credentials. """
        if not self.credentials:
            sts_client = self.session.client('sts', region_name=self.region)
            try:
                assumed_role_object = sts_client.assume_role(
                    RoleArn=self.role_arn,
                    RoleSessionName="AssumedRoleSession1",
                    ExternalId=self.seller_id
                )
                self.credentials = assumed_role_object['Credentials']
            except ClientError as e:
                logger.error(f"Error assuming role: {e}")
                raise
        return self.credentials

    # auth
    def create_auth(self):
        ''' Create auth AWS4Auth for API requests.'''
        if not self.auth:
            credentials = self.assume_role()
            self.auth = AWS4Auth(
                credentials['AccessKeyId'],
                credentials['SecretAccessKey'],
                self.region,
                'execute-api',
                session_token=credentials['SessionToken']
            )
        return self.auth

    # auth
    def get_lwa_access_token(self):
        now = datetime.now(timezone.utc)

        if (
            not self.lwa_token
            or not self.lwa_token_expires_at
            or now >= self.lwa_token_expires_at
        ):
            data = {
                "grant_type": "refresh_token",
                "client_id": LWA_CLIENT_ID,
                "client_secret": LWA_CLIENT_SECRET,
                "refresh_token": LWA_REFRESH_TOKEN
            }
            try :

                response = requests.post(LWA_TOKEN_URL, data=data)
                response.raise_for_status()

                self.lwa_token = response.json()["access_token"]
                expires_in = response.json().get("expires_in", 3600)

                self.lwa_token_expires_at = now + timedelta(seconds=expires_in - 60)
            except RequestException as e :
                logger.error(f"Error obtaining LWA token: {e}")
        return self.lwa_token

    # auth
    def get_lwa_acess_token_grantless(self, scope: str):
        data = {
            "grant_type": "client_credentials",
            "client_id": LWA_CLIENT_ID,
            "client_secret": LWA_CLIENT_SECRET,
            "scope": scope,
        }
        reponse = requests.post(LWA_TOKEN_URL, data=data)
        reponse.raise_for_status()
        return reponse.json()["access_token"]


    # auth
    def create_headers_lwa(self):
        ''' Creates the headers for API requests. '''
        lwa_token = self.get_lwa_access_token()
        return {
            # "Authorization": f"Bearer {lwa_token}",
            "x-amz-access-token": lwa_token,
            "content-type": "application/json"
        }

    # auth
    def create_headers_grantless(self):
        grantless_token = self.get_lwa_acess_token_grantless(
            scope="sellingpartnerapi::notifications"
        )
        return {
            "x-amz-access-token": grantless_token,
            "content-type": "application/json"
        }

    # base client
    # This class should only receive auth and headers
    # And make the basic request handling.
    def make_request(self, url, method="GET", headers=None, json_body=None):
        auth = self.create_auth()
        if headers is None:
            headers = self.create_headers_lwa()

        try:
            method = method.upper()

            if method == "GET":
                response = requests.get(url, auth=auth, headers=headers)

            elif method == "POST":
                response = requests.post(url, auth=auth, headers=headers, json=json_body)

            else:
                raise ValueError(f"Unsupported method: {method}")

            if not response.ok:
                logger.error(
                    "SP-API error %s for %s\nResponse: %s",
                    response.status_code, url, response.text
                )

            response.raise_for_status()

            # Some SP-API endpoints can return empty bodies; handle that safely:
            if not response.text:
                return None

            return response.json()

        except RequestException as e:
            logger.error(f"Error making request: {e} , url: {url}")
            raise

    # base client
    def build_url(self, path, params):
        url = urljoin(self.endpoint, path)
        if not params:
            return url
        return f"{url}?{urlencode(params)}"

    # base client
    def to_iso_z(self, dt) -> str:
        # Convert to ISO 8601 with Z for UTC
        iso = dt.isoformat()
        return iso.replace("+00:00", "Z")
