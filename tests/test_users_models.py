"""
Tests for User and OAuthToken domain models.
"""

from datetime import datetime, UTC

import pytest

from app.users.models import OAuthToken, User


class TestOAuthToken:
    """Tests for OAuthToken model."""

    def test_create_token_with_required_fields(self):
        """Test creating token with minimum required fields."""
        token = OAuthToken(
            provider="google",
            access_token="test-access-token",
        )

        assert token.provider == "google"
        assert token.access_token == "test-access-token"
        assert token.refresh_token is None
        assert token.expires_at is None
        assert token.token_type == "Bearer"
        assert token.scope is None

    def test_create_token_with_all_fields(self):
        """Test creating token with all fields."""
        token = OAuthToken(
            provider="google",
            access_token="test-access-token",
            refresh_token="test-refresh-token",
            expires_at=1700000000,
            token_type="Bearer",
            scope="openid email profile",
        )

        assert token.provider == "google"
        assert token.access_token == "test-access-token"
        assert token.refresh_token == "test-refresh-token"
        assert token.expires_at == 1700000000
        assert token.scope == "openid email profile"

    def test_from_oauth_response(self):
        """Test creating token from authlib response dict."""
        oauth_response = {
            "access_token": "ya29.access-token",
            "refresh_token": "1//refresh-token",
            "expires_at": 1700000000,
            "token_type": "Bearer",
            "scope": "openid email",
        }

        token = OAuthToken.from_oauth_response("google", oauth_response)

        assert token.provider == "google"
        assert token.access_token == "ya29.access-token"
        assert token.refresh_token == "1//refresh-token"
        assert token.expires_at == 1700000000

    def test_from_oauth_response_minimal(self):
        """Test creating token from minimal oauth response."""
        oauth_response = {
            "access_token": "test-token",
        }

        token = OAuthToken.from_oauth_response("adobe", oauth_response)

        assert token.provider == "adobe"
        assert token.access_token == "test-token"
        assert token.refresh_token is None

    def test_to_authlib_token(self):
        """Test converting token back to authlib format."""
        token = OAuthToken(
            provider="google",
            access_token="test-access",
            refresh_token="test-refresh",
            expires_at=1700000000,
            token_type="Bearer",
            scope="openid",
        )

        authlib_token = token.to_authlib_token()

        assert authlib_token["access_token"] == "test-access"
        assert authlib_token["refresh_token"] == "test-refresh"
        assert authlib_token["expires_at"] == 1700000000
        assert authlib_token["token_type"] == "Bearer"
        assert authlib_token["scope"] == "openid"

    def test_is_expired_with_future_expiry(self):
        """Test token is not expired when expires_at is in future."""
        future_timestamp = datetime.now(UTC).timestamp() + 3600  # 1 hour from now
        token = OAuthToken(
            provider="google",
            access_token="test",
            expires_at=int(future_timestamp),
        )

        assert not token.is_expired()

    def test_is_expired_with_past_expiry(self):
        """Test token is expired when expires_at is in past."""
        past_timestamp = datetime.now(UTC).timestamp() - 3600  # 1 hour ago
        token = OAuthToken(
            provider="google",
            access_token="test",
            expires_at=int(past_timestamp),
        )

        assert token.is_expired()

    def test_is_expired_without_expiry(self):
        """Test token without expires_at is never expired."""
        token = OAuthToken(
            provider="google",
            access_token="test",
            expires_at=None,
        )

        assert not token.is_expired()

    def test_connected_at_default(self):
        """Test connected_at is set to current time by default."""
        before = datetime.now(UTC)
        token = OAuthToken(provider="google", access_token="test")
        after = datetime.now(UTC)

        assert before <= token.connected_at <= after


class TestUser:
    """Tests for User model."""

    def test_create_user_with_required_fields(self):
        """Test creating user with minimum required fields."""
        user = User(uid="firebase-uid-123", email="test@example.com")

        assert user.uid == "firebase-uid-123"
        assert user.email == "test@example.com"
        assert user.tokens == {}

    def test_create_user_with_tokens(self):
        """Test creating user with existing tokens."""
        google_token = OAuthToken(provider="google", access_token="google-token")
        user = User(
            uid="firebase-uid-123",
            email="test@example.com",
            tokens={"google": google_token},
        )

        assert "google" in user.tokens
        assert user.tokens["google"].access_token == "google-token"

    def test_get_token_exists(self):
        """Test getting a token that exists."""
        token = OAuthToken(provider="google", access_token="test-token")
        user = User(
            uid="uid-123",
            email="test@example.com",
            tokens={"google": token},
        )

        result = user.get_token("google")
        assert result is not None
        assert result.access_token == "test-token"

    def test_get_token_not_exists(self):
        """Test getting a token that doesn't exist."""
        user = User(uid="uid-123", email="test@example.com")

        result = user.get_token("google")
        assert result is None

    def test_has_connection_true(self):
        """Test has_connection returns True when connected."""
        token = OAuthToken(provider="google", access_token="test")
        user = User(
            uid="uid-123",
            email="test@example.com",
            tokens={"google": token},
        )

        assert user.has_connection("google") is True

    def test_has_connection_false(self):
        """Test has_connection returns False when not connected."""
        user = User(uid="uid-123", email="test@example.com")

        assert user.has_connection("google") is False

    def test_connected_providers_empty(self):
        """Test connected_providers with no connections."""
        user = User(uid="uid-123", email="test@example.com")

        assert user.connected_providers() == []

    def test_connected_providers_multiple(self):
        """Test connected_providers with multiple connections."""
        user = User(
            uid="uid-123",
            email="test@example.com",
            tokens={
                "google": OAuthToken(provider="google", access_token="g-token"),
                "adobe": OAuthToken(provider="adobe", access_token="a-token"),
            },
        )

        providers = user.connected_providers()
        assert set(providers) == {"google", "adobe"}

    def test_timestamps_default(self):
        """Test created_at and updated_at are set by default."""
        before = datetime.now(UTC)
        user = User(uid="uid-123", email="test@example.com")
        after = datetime.now(UTC)

        assert before <= user.created_at <= after
        assert before <= user.updated_at <= after

    def test_email_validation(self):
        """Test email field validates email format."""
        with pytest.raises(ValueError):
            User(uid="uid-123", email="not-an-email")
