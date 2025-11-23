"""
Tests for OAuth configuration and provider registry.
"""

import os
from unittest.mock import patch

import pytest

from app.oauth.config import (
    OAuthConfig,
    get_oauth_config,
    create_oauth_registry,
    SUPPORTED_PROVIDERS,
    reset_oauth_registry,
)


class TestOAuthConfig:
    """Tests for OAuthConfig."""

    def test_from_env_loads_variables(self):
        """Test loading config from environment variables."""
        env = {
            "BASE_URL": "https://example.com",
            "GOOGLE_CLIENT_ID": "google-id",
            "GOOGLE_CLIENT_SECRET": "google-secret",
            "ADOBE_CLIENT_ID": "adobe-id",
            "ADOBE_CLIENT_SECRET": "adobe-secret",
        }

        with patch.dict(os.environ, env, clear=False):
            config = OAuthConfig.from_env()

        assert config.base_url == "https://example.com"
        assert config.google_client_id == "google-id"
        assert config.google_client_secret == "google-secret"
        assert config.adobe_client_id == "adobe-id"
        assert config.adobe_client_secret == "adobe-secret"

    def test_from_env_handles_missing(self):
        """Test loading config with missing variables."""
        with patch.dict(os.environ, {"BASE_URL": "https://example.com"}, clear=True):
            config = OAuthConfig.from_env()

        assert config.base_url == "https://example.com"
        assert config.google_client_id is None
        assert config.google_client_secret is None

    def test_get_callback_url(self):
        """Test callback URL generation."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id=None,
            google_client_secret=None,
        )

        assert config.get_callback_url("google") == "https://example.com/oauth/google/callback"
        assert config.get_callback_url("adobe") == "https://example.com/oauth/adobe/callback"

    def test_is_provider_configured_google_true(self):
        """Test Google provider is configured when credentials exist."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="id",
            google_client_secret="secret",
        )

        assert config.is_provider_configured("google") is True

    def test_is_provider_configured_google_false_missing_id(self):
        """Test Google not configured when client_id missing."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id=None,
            google_client_secret="secret",
        )

        assert config.is_provider_configured("google") is False

    def test_is_provider_configured_google_false_missing_secret(self):
        """Test Google not configured when client_secret missing."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="id",
            google_client_secret=None,
        )

        assert config.is_provider_configured("google") is False

    def test_is_provider_configured_adobe(self):
        """Test Adobe provider configuration check."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id=None,
            google_client_secret=None,
            adobe_client_id="adobe-id",
            adobe_client_secret="adobe-secret",
        )

        assert config.is_provider_configured("adobe") is True
        assert config.is_provider_configured("google") is False

    def test_is_provider_configured_unknown(self):
        """Test unknown provider returns False."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="id",
            google_client_secret="secret",
        )

        assert config.is_provider_configured("unknown") is False

    def test_get_configured_providers_none(self):
        """Test getting configured providers when none configured."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id=None,
            google_client_secret=None,
        )

        assert config.get_configured_providers() == []

    def test_get_configured_providers_google_only(self):
        """Test getting configured providers with only Google."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="id",
            google_client_secret="secret",
        )

        assert config.get_configured_providers() == ["google"]

    def test_get_configured_providers_both(self):
        """Test getting configured providers with both."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="g-id",
            google_client_secret="g-secret",
            adobe_client_id="a-id",
            adobe_client_secret="a-secret",
        )

        providers = config.get_configured_providers()
        assert set(providers) == {"google", "adobe"}


class TestOAuthRegistry:
    """Tests for OAuth registry creation."""

    def test_create_registry_no_providers(self):
        """Test creating registry with no providers configured."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id=None,
            google_client_secret=None,
        )

        oauth = create_oauth_registry(config)

        # Registry should exist but have no configured clients
        assert oauth is not None

    def test_create_registry_with_google(self):
        """Test creating registry with Google configured."""
        config = OAuthConfig(
            base_url="https://example.com",
            google_client_id="google-id",
            google_client_secret="google-secret",
        )

        oauth = create_oauth_registry(config)

        # Should be able to create Google client
        client = oauth.create_client("google")
        assert client is not None

    def test_reset_oauth_registry(self):
        """Test resetting the OAuth registry."""
        # This should not raise
        reset_oauth_registry()


class TestSupportedProviders:
    """Tests for supported providers list."""

    def test_supported_providers_includes_google(self):
        """Test Google is in supported providers."""
        assert "google" in SUPPORTED_PROVIDERS

    def test_supported_providers_includes_adobe(self):
        """Test Adobe is in supported providers."""
        assert "adobe" in SUPPORTED_PROVIDERS
