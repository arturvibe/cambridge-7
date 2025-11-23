"""
FastAPI dependencies for authentication.

Provides dependency injection for session validation.
"""

import logging
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status

from app.auth.config import get_auth_config, AuthConfig
from app.auth.services import (
    AuthenticationError,
    SessionCookieService,
)


logger = logging.getLogger(__name__)


def get_session_cookie_service() -> SessionCookieService:
    """Provide SessionCookieService dependency."""
    return SessionCookieService()


async def get_current_user(
    session: Annotated[str | None, Cookie()] = None,
    config: AuthConfig = Depends(get_auth_config),
    session_service: SessionCookieService = Depends(get_session_cookie_service),
) -> dict:
    """
    Dependency to get the current authenticated user.

    Validates the session cookie and returns user claims.

    Args:
        session: Session cookie from request
        config: Auth configuration
        session_service: Service for session validation

    Returns:
        Decoded user claims from session cookie

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not session:
        logger.warning("No session cookie provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no session cookie",
        )

    try:
        claims = session_service.verify_session_cookie(session)
        return claims
    except AuthenticationError as e:
        logger.warning(f"Session validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
