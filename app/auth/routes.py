"""
Authentication API routes.

Provides endpoints for magic link authentication flow:
- POST /login: Generate magic link
- GET /auth/callback: Handle magic link callback
- GET /dashboard: Protected resource
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel, EmailStr

from app.auth.config import get_auth_config, AuthConfig
from app.auth.dependencies import get_current_user
from app.auth.services import (
    AuthenticationError,
    MagicLinkService,
    SessionCookieService,
    TokenExchangeService,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================


class LoginRequest(BaseModel):
    """Request body for login endpoint."""

    email: EmailStr


class LoginResponse(BaseModel):
    """Response for login endpoint."""

    status: str
    message: str


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    config: AuthConfig = Depends(get_auth_config),
) -> LoginResponse:
    """
    Generate a magic link for email authentication.

    The magic link will be printed to the server logs.
    The user should copy this link and paste it into their browser.

    Args:
        request: Contains the user's email address
        config: Auth configuration

    Returns:
        Success message indicating the link was generated
    """
    try:
        # Validate configuration
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    try:
        magic_link_service = MagicLinkService()
        magic_link = magic_link_service.generate_magic_link(request.email)

        # Print the magic link to server logs
        logger.info("=" * 80)
        logger.info("MAGIC LINK GENERATED")
        logger.info("=" * 80)
        logger.info(f"Email: {request.email}")
        logger.info(f"Magic Link: {magic_link}")
        logger.info("=" * 80)
        logger.info("Copy and paste this link in your browser to authenticate")
        logger.info("=" * 80)

        # Also print to stdout for easier access in development
        print("\n" + "=" * 80)
        print("MAGIC LINK GENERATED")
        print("=" * 80)
        print(f"Email: {request.email}")
        print(f"Magic Link: {magic_link}")
        print("=" * 80)
        print("Copy and paste this link in your browser to authenticate")
        print("=" * 80 + "\n")

        return LoginResponse(
            status="success",
            message="Magic link generated - check server logs",
        )

    except AuthenticationError as e:
        logger.error(f"Failed to generate magic link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/auth/callback")
async def auth_callback(
    oobCode: Annotated[str, Query(description="One-time out-of-band code")],
    email: Annotated[
        str | None,
        Query(description="User email (may be in continueUrl or mode)"),
    ] = None,
    mode: Annotated[str | None, Query(description="Firebase action mode")] = None,
    continueUrl: Annotated[
        str | None, Query(description="Continue URL after authentication")
    ] = None,
    config: AuthConfig = Depends(get_auth_config),
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
        email: User's email address (optional, extracted from link)
        mode: Firebase action mode (e.g., 'signIn')
        continueUrl: URL to continue to after auth
        config: Auth configuration

    Returns:
        Redirect response with session cookie set
    """
    logger.info(f"Auth callback received - oobCode present: {bool(oobCode)}")

    if not oobCode:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing oobCode parameter",
        )

    # Email is required for the sign-in process
    if not email:
        logger.error("Email not provided in callback")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email parameter is required. Please use the magic link "
            "with the same email address you requested.",
        )

    try:
        # Step 1: Exchange oobCode for ID token
        token_service = TokenExchangeService()
        id_token = await token_service.exchange_oob_code_for_id_token(
            oob_code=oobCode,
            email=email,
        )

        # Step 2: Create session cookie
        session_service = SessionCookieService()
        session_cookie = session_service.create_session_cookie(id_token)

        # Step 3: Create redirect response with cookie
        response = RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_302_FOUND,
        )

        # Set the session cookie
        response.set_cookie(
            key=config.session_cookie_name,
            value=session_cookie,
            max_age=config.session_cookie_max_age,
            httponly=True,
            secure=config.base_url.startswith("https"),
            samesite="lax",
        )

        logger.info(f"Authentication successful, redirecting to dashboard")
        return response

    except AuthenticationError as e:
        logger.error(f"Authentication callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get("/dashboard")
async def dashboard(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Protected dashboard endpoint.

    Requires a valid session cookie to access.

    Args:
        current_user: User claims from validated session cookie

    Returns:
        Welcome message with user information
    """
    user_email = current_user.get("email", "unknown")
    user_uid = current_user.get("uid", "unknown")

    logger.info(f"Dashboard accessed by user: {user_uid}")

    return {
        "status": "success",
        "message": "Welcome, you are authenticated!",
        "user": {
            "uid": user_uid,
            "email": user_email,
        },
    }
