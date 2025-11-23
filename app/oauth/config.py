"""
OAuth2 configuration and provider registry.

Uses authlib to manage OAuth2 clients for multiple providers.
Each provider (Google, Adobe, etc.) can be configured independently.
"""

import os
import logging
from dataclasses import dataclass
from functools import lru_cache

from authlib.integrations.starlette_client import OAuth


logger = logging.getLogger(__name__)


@dataclass
class OAuthConfig:
    """
    OAuth configuration settings.

    Loaded from environment variables. Validates required settings at startup.
    """

    base_url: str
    google_client_id: str | None
    google_client_secret: str | None

    # Adobe (future)
    adobe_client_id: str | None = None
    adobe_client_secret: str | None = None

    @classmethod
    def from_env(cls) -> "OAuthConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.getenv("BASE_URL", ""),
            google_client_id=os.getenv("GOOGLE_CLIENT_ID"),
            google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            adobe_client_id=os.getenv("ADOBE_CLIENT_ID"),
            adobe_client_secret=os.getenv("ADOBE_CLIENT_SECRET"),
        )

    def get_callback_url(self, provider: str) -> str:
        """Generate callback URL for a provider."""
        return f"{self.base_url}/oauth/{provider}/callback"

    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider has valid credentials configured."""
        if provider == "google":
            return bool(self.google_client_id and self.google_client_secret)
        if provider == "adobe":
            return bool(self.adobe_client_id and self.adobe_client_secret)
        return False

    def get_configured_providers(self) -> list[str]:
        """List all providers with valid configuration."""
        providers = []
        if self.is_provider_configured("google"):
            providers.append("google")
        if self.is_provider_configured("adobe"):
            providers.append("adobe")
        return providers


@lru_cache()
def get_oauth_config() -> OAuthConfig:
    """Get OAuth configuration singleton."""
    return OAuthConfig.from_env()


def create_oauth_registry(config: OAuthConfig | None = None) -> OAuth:
    """
    Create and configure the authlib OAuth registry.

    Registers all configured OAuth providers. Providers without
    credentials are skipped (allows partial configuration).

    Args:
        config: OAuth configuration (uses default if not provided)

    Returns:
        Configured OAuth registry
    """
    if config is None:
        config = get_oauth_config()

    oauth = OAuth()

    # Register Google OAuth2
    if config.is_provider_configured("google"):
        oauth.register(
            name="google",
            client_id=config.google_client_id,
            client_secret=config.google_client_secret,
            server_metadata_url=(
                "https://accounts.google.com/.well-known/openid-configuration"
            ),
            client_kwargs={
                "scope": "openid email profile",
                # Add service-specific scopes as needed:
                # "https://www.googleapis.com/auth/photoslibrary"
            },
        )
        logger.info("Registered Google OAuth provider")
    else:
        logger.warning("Google OAuth not configured (missing credentials)")

    # Register Adobe OAuth2 for Frame.io
    if config.is_provider_configured("adobe"):
        oauth.register(
            name="adobe",
            client_id=config.adobe_client_id,
            client_secret=config.adobe_client_secret,
            authorize_url="https://ims-na1.adobelogin.com/ims/authorize/v2",
            access_token_url="https://ims-na1.adobelogin.com/ims/token/v3",
            client_kwargs={
                "scope": "openid email profile frame.io.read frame.io.write",
            },
        )
        logger.info("Registered Adobe OAuth provider")
    else:
        logger.debug("Adobe OAuth not configured (missing credentials)")

    return oauth


# Global OAuth registry singleton
_oauth_registry: OAuth | None = None


def get_oauth_registry() -> OAuth:
    """
    Get the OAuth registry singleton.

    Creates and configures the registry on first access.
    """
    global _oauth_registry
    if _oauth_registry is None:
        _oauth_registry = create_oauth_registry()
    return _oauth_registry


def reset_oauth_registry() -> None:
    """
    Reset the OAuth registry.

    Useful for testing with different configurations.
    """
    global _oauth_registry
    _oauth_registry = None


# List of supported providers (for validation)
SUPPORTED_PROVIDERS = ["google", "adobe"]
