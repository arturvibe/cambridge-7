"""
Magic link authentication API endpoints.

This is a driving adapter that exposes HTTP endpoints for magic link
authentication and delegates to the auth services.

The adapter is "dumb" - it only translates HTTP to Python and back.
All business logic lives in the service layer.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, EmailStr

from app.auth.config import get_auth_config, AuthConfig
from app.auth.services import (
    AuthenticationError,
    MagicLinkService,
    SessionCookieService,
    TokenExchangeService,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/magic", tags=["authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================


class MagicLinkRequest(BaseModel):
    """Request body for magic link send endpoint."""

    email: EmailStr


class MagicLinkResponse(BaseModel):
    """Response for magic link send endpoint."""

    status: str
    message: str


# ============================================================================
# Dependency Functions
# ============================================================================


def get_magic_link_service() -> MagicLinkService:
    """Provide MagicLinkService dependency."""
    return MagicLinkService()


def get_token_exchange_service() -> TokenExchangeService:
    """Provide TokenExchangeService dependency."""
    return TokenExchangeService()


def get_session_cookie_service() -> SessionCookieService:
    """Provide SessionCookieService dependency."""
    return SessionCookieService()


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/send", response_model=MagicLinkResponse)
async def send_magic_link(
    request: MagicLinkRequest,
    config: AuthConfig = Depends(get_auth_config),
    magic_link_service: MagicLinkService = Depends(get_magic_link_service),
) -> MagicLinkResponse:
    """
    Generate and send a magic link for email authentication.

    The magic link will be printed to the server logs for local testing.
    Copy this link and paste it into your browser to authenticate.

    Args:
        request: Contains the user's email address
        config: Auth configuration
        magic_link_service: Service for generating magic links

    Returns:
        Success message indicating the link was generated
    """
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    try:
        magic_link = magic_link_service.generate_magic_link(request.email)

        # Log the magic link for local testing
        logger.info("=" * 80)
        logger.info("MAGIC LINK GENERATED")
        logger.info("=" * 80)
        logger.info(f"Email: {request.email}")
        logger.info(f"Magic Link: {magic_link}")
        logger.info("=" * 80)
        logger.info("Copy and paste this link in your browser to authenticate")
        logger.info("=" * 80)

        return MagicLinkResponse(
            status="success",
            message="Magic link generated - check server logs",
        )

    except AuthenticationError as e:
        logger.error(f"Failed to generate magic link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/callback")
async def magic_link_callback(
    oobCode: Annotated[
        str, Query(description="One-time out-of-band code from Firebase")
    ],
    email: Annotated[str | None, Query(description="User email address")] = None,
    mode: Annotated[str | None, Query(description="Firebase action mode")] = None,
    continueUrl: Annotated[str | None, Query(description="Continue URL")] = None,
    config: AuthConfig = Depends(get_auth_config),
    token_service: TokenExchangeService = Depends(get_token_exchange_service),
    session_service: SessionCookieService = Depends(get_session_cookie_service),
) -> Response:
    """
    Handle the magic link callback from Firebase.

    This endpoint:
    1. Receives the oobCode from Firebase
    2. Exchanges it for an ID token via Firebase REST API
    3. Creates a session cookie
    4. Sets the cookie in the response
    5. Redirects to /dashboard

    Args:
        oobCode: The one-time code from the magic link
        email: User's email address
        mode: Firebase action mode (e.g., 'signIn')
        continueUrl: URL to continue to after auth
        config: Auth configuration
        token_service: Service for exchanging oobCode for ID token
        session_service: Service for creating session cookies

    Returns:
        Redirect response with session cookie set
    """
    logger.info(f"Magic link callback received - oobCode present: {bool(oobCode)}")

    if not email:
        logger.error("Email not provided in callback")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email parameter is required. Please use the magic link "
            "with the same email address you requested.",
        )

    try:
        # Exchange oobCode for ID token
        id_token = await token_service.exchange_oob_code_for_id_token(
            oob_code=oobCode,
            email=email,
        )

        # Create session cookie
        session_cookie = session_service.create_session_cookie(id_token)

        # Create redirect response with cookie
        response = RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_302_FOUND,
        )

        response.set_cookie(
            key=config.session_cookie_name,
            value=session_cookie,
            max_age=config.session_cookie_max_age,
            httponly=True,
            secure=config.base_url.startswith("https"),
            samesite="lax",
        )

        logger.info("Authentication successful, redirecting to dashboard")
        return response

    except AuthenticationError as e:
        logger.error(f"Authentication callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


# ============================================================================
# Protected Endpoint (Dashboard)
# ============================================================================


@router.get("/dashboard", include_in_schema=False)
async def dashboard_redirect():
    """Redirect /auth/magic/dashboard to /dashboard."""
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
