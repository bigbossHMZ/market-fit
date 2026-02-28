import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from apps.backend.clients.spapi.auth import StsAuth
from apps.backend.clients.spapi.config import StsConfig
from apps.backend.clients.spapi.errors import SPAPIAuthError


def _make_config() -> StsConfig:
    return StsConfig(
        role_arn="arn:aws:iam::123456789012:role/SPAPIRole",
        region="us-east-1",
        seller_id="SELLER123",
    )


def _make_credentials(minutes_until_expiry: int = 60) -> dict:
    """Builds a mock STS credentials dict with a configurable expiration."""
    return {
        "AccessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "SecretAccessKey": "secret-key",
        "SessionToken": "session-token",
        "Expiration": datetime.now(timezone.utc) + timedelta(minutes=minutes_until_expiry),
    }


def _make_assume_role_response(credentials: dict) -> dict:
    return {"Credentials": credentials}


class TestIsExpired:
    def test_returns_true_when_credentials_are_empty(self):
        auth = StsAuth(_make_config())
        assert auth._is_expired() is True

    def test_returns_true_when_expiry_within_5_minutes(self):
        auth = StsAuth(_make_config())
        auth.credentials = _make_credentials(minutes_until_expiry=3)
        assert auth._is_expired() is True

    def test_returns_false_when_credentials_are_fresh(self):
        auth = StsAuth(_make_config())
        auth.credentials = _make_credentials(minutes_until_expiry=60)
        assert auth._is_expired() is False


class TestAssumeRole:
    def test_calls_boto3_with_correct_args(self):
        config = _make_config()
        auth = StsAuth(config)
        credentials = _make_credentials()

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(credentials)

            auth._assume_role()

            mock_boto3.assert_called_once_with("sts", region_name=config.region)
            mock_sts.assume_role.assert_called_once_with(
                RoleArn=config.role_arn,
                RoleSessionName="AssumedRoleSession1",
                ExternalId=config.seller_id,
            )

    def test_caches_credentials_after_first_call(self):
        auth = StsAuth(_make_config())
        credentials = _make_credentials()

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(credentials)

            auth._assume_role()
            auth._assume_role()

            mock_sts.assume_role.assert_called_once()

    def test_refreshes_when_credentials_are_expired(self):
        auth = StsAuth(_make_config())
        auth.credentials = _make_credentials(minutes_until_expiry=3)

        fresh_credentials = _make_credentials(minutes_until_expiry=60)

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(fresh_credentials)

            result = auth._assume_role()

            mock_sts.assume_role.assert_called_once()
            assert result == fresh_credentials

    def test_raises_spapi_auth_error_on_boto3_failure(self):
        auth = StsAuth(_make_config())

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.side_effect = Exception("AccessDenied")

            with pytest.raises(SPAPIAuthError, match="STS role assumption failed"):
                auth._assume_role()

    def test_invalidates_aws_auth_cache_on_refresh(self):
        auth = StsAuth(_make_config())
        auth.credentials = _make_credentials(minutes_until_expiry=3)
        auth._aws_auth = MagicMock()  # simulate a cached signer

        fresh_credentials = _make_credentials(minutes_until_expiry=60)

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(fresh_credentials)

            auth._assume_role()

            assert auth._aws_auth is None


class TestGetAwsAuth:
    def test_builds_aws4auth_from_credentials(self):
        auth = StsAuth(_make_config())
        credentials = _make_credentials()

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(credentials)

            with patch("apps.backend.clients.spapi.auth.AWS4Auth") as mock_aws4auth:
                auth.get_aws_auth()
                mock_aws4auth.assert_called_once_with(
                    credentials["AccessKeyId"],
                    credentials["SecretAccessKey"],
                    auth.config.region,
                    "execute-api",
                    session_token=credentials["SessionToken"],
                )

    def test_caches_aws4auth_object(self):
        auth = StsAuth(_make_config())
        credentials = _make_credentials()

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(credentials)

            with patch("apps.backend.clients.spapi.auth.AWS4Auth") as mock_aws4auth:
                auth.get_aws_auth()
                auth.get_aws_auth()
                mock_aws4auth.assert_called_once()

    def test_rebuilds_aws4auth_after_credential_refresh(self):
        auth = StsAuth(_make_config())
        auth.credentials = _make_credentials(minutes_until_expiry=3)

        fresh_credentials = _make_credentials(minutes_until_expiry=60)

        with patch("apps.backend.clients.spapi.auth.boto3.client") as mock_boto3:
            mock_sts = MagicMock()
            mock_boto3.return_value = mock_sts
            mock_sts.assume_role.return_value = _make_assume_role_response(fresh_credentials)

            with patch("apps.backend.clients.spapi.auth.AWS4Auth") as mock_aws4auth:
                auth.get_aws_auth()
                mock_aws4auth.assert_called_once_with(
                    fresh_credentials["AccessKeyId"],
                    fresh_credentials["SecretAccessKey"],
                    auth.config.region,
                    "execute-api",
                    session_token=fresh_credentials["SessionToken"],
                )
