"""
OAuth2 API endpoints.

Provides the minimal API surface for OAuth2 service integrations:
- GET /oauth/{provider}/connect - Start OAuth flow
- GET /oauth/{provider}/callback - Handle callback, store tokens

Additional endpoints (list connections, disconnect) can be added later.
"""

import logging

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.oauth.config import get_oauth_config
from app.oauth.dependencies import (
    CurrentUser,
    OAuthRegistry,
    Repository,
    ValidProvider,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/oauth", tags=["oauth"])


@router.get("/{provider}/connect")
async def connect(
    provider: ValidProvider,
    request: Request,
    user: CurrentUser,
    oauth: OAuthRegistry,
):
    """
    Start OAuth2 authorization flow.

    Redirects the user to the OAuth provider's authorization page.
    Authlib handles state parameter and PKCE automatically.

    Requires authentication (magic link session).

    Args:
        provider: OAuth provider name (google, adobe)
        request: Starlette request (for redirect)
        user: Current authenticated user
        oauth: OAuth registry

    Returns:
        Redirect to provider's authorization page
    """
    config = get_oauth_config()
    redirect_uri = config.get_callback_url(provider)

    logger.info(
        f"Starting OAuth flow for provider: {provider}",
        extra={"user_uid": user.get("uid"), "provider": provider},
    )

    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth client for '{provider}' not available",
        )

    return await client.authorize_redirect(request, redirect_uri)


@router.get("/{provider}/callback")
async def callback(
    provider: ValidProvider,
    request: Request,
    user: CurrentUser,
    oauth: OAuthRegistry,
    repository: Repository,
):
    """
    Handle OAuth2 callback from provider.

    Exchanges the authorization code for tokens and stores them.
    Redirects to dashboard on success.

    Args:
        provider: OAuth provider name
        request: Starlette request (contains auth code)
        user: Current authenticated user
        oauth: OAuth registry
        repository: User repository for token storage

    Returns:
        Redirect to dashboard on success

    Raises:
        HTTPException: On OAuth errors
    """
    user_uid: str = user["uid"]

    logger.info(
        f"OAuth callback received for provider: {provider}",
        extra={"user_uid": user_uid, "provider": provider},
    )

    client = oauth.create_client(provider)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"OAuth client for '{provider}' not available",
        )

    try:
        # Exchange authorization code for tokens
        token = await client.authorize_access_token(request)
    except OAuthError as e:
        logger.error(
            f"OAuth error during token exchange: {e}",
            extra={"user_uid": user_uid, "provider": provider, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"OAuth authorization failed: {e.description or str(e)}",
        )

    # Store tokens in repository
    await repository.save_token(user_uid, provider, dict(token))

    logger.info(
        f"Successfully connected {provider} for user",
        extra={"user_uid": user_uid, "provider": provider},
    )

    # Redirect to dashboard with success indicator
    return RedirectResponse(
        url=f"/dashboard?connected={provider}",
        status_code=status.HTTP_302_FOUND,
    )


# =============================================================================
# Optional endpoints (can be implemented later in parallel)
# =============================================================================


@router.get("/connections")
async def list_connections(
    user: CurrentUser,
    repository: Repository,
):
    """
    List user's connected OAuth services.

    Args:
        user: Current authenticated user
        repository: User repository

    Returns:
        List of connected provider names
    """
    user_uid: str = user["uid"]
    connections = await repository.list_connections(user_uid)

    return {
        "status": "success",
        "connections": connections,
    }


@router.delete("/{provider}")
async def disconnect(
    provider: ValidProvider,
    user: CurrentUser,
    repository: Repository,
):
    """
    Disconnect an OAuth service.

    Removes stored tokens for the provider.

    Args:
        provider: OAuth provider to disconnect
        user: Current authenticated user
        repository: User repository

    Returns:
        Success message
    """
    user_uid: str = user["uid"]

    deleted = await repository.delete_token(user_uid, provider)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No connection found for provider: {provider}",
        )

    logger.info(
        f"Disconnected {provider} for user",
        extra={"user_uid": user_uid, "provider": provider},
    )

    return {
        "status": "success",
        "message": f"Disconnected from {provider}",
    }
