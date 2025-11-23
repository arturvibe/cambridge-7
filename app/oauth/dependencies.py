"""
FastAPI dependencies for OAuth endpoints.

Provides dependency injection for OAuth services and user validation.
"""

import logging
from typing import Annotated

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.oauth.config import (
    get_oauth_config,
    get_oauth_registry,
    OAuthConfig,
    SUPPORTED_PROVIDERS,
)
from app.users.repository import get_user_repository, UserRepository


logger = logging.getLogger(__name__)


def get_oauth(
    config: Annotated[OAuthConfig, Depends(get_oauth_config)],
) -> OAuth:
    """
    Provide OAuth registry dependency.

    The registry is a singleton, but we pass config for potential testing.
    """
    return get_oauth_registry()


def get_repository() -> UserRepository:
    """Provide UserRepository dependency."""
    return get_user_repository()


async def validate_provider(provider: str) -> str:
    """
    Validate that the provider is supported and configured.

    Args:
        provider: OAuth provider name from path

    Returns:
        Validated provider name

    Raises:
        HTTPException: If provider is invalid or not configured
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown provider: {provider}. Supported: {SUPPORTED_PROVIDERS}",
        )

    config = get_oauth_config()
    if not config.is_provider_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider '{provider}' is not configured",
        )

    return provider


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[dict, Depends(get_current_user)]
ValidProvider = Annotated[str, Depends(validate_provider)]
OAuthRegistry = Annotated[OAuth, Depends(get_oauth)]
Repository = Annotated[UserRepository, Depends(get_repository)]
