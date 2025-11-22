"""
Magic Link Authentication Endpoints.
"""

import os
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr

from app.core.auth_service import AuthService

# Router for authentication endpoints
router = APIRouter(prefix="/auth/magic", tags=["auth"])

# Router for the protected dashboard (exposed at root level)
dashboard_router = APIRouter(tags=["dashboard"])


class MagicLinkRequest(BaseModel):
    email: EmailStr


def get_auth_service_dependency() -> AuthService:
    """
    Placeholder dependency for AuthService.
    Wired in main.py.
    """
    raise NotImplementedError("AuthService dependency must be configured")


async def get_current_user(
    request: Request, auth_service: AuthService = Depends(get_auth_service_dependency)
) -> Dict:
    """
    Dependency to verify session cookie and return user claims.
    """
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        claims = await auth_service.verify_session(session_cookie)
        return claims
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        )


@router.post("/send")
async def send_magic_link(
    request: MagicLinkRequest,
    req: Request,
    auth_service: AuthService = Depends(get_auth_service_dependency),
):
    """
    Generate and log a magic link for the given email.
    """
    try:
        # Extract base URL from request
        base_url = str(req.base_url)

        # If running in Cloud Run (K_SERVICE exists), ensure HTTPS
        if os.getenv("K_SERVICE") and base_url.startswith("http://"):
            base_url = base_url.replace("http://", "https://", 1)

        # The service handles generating the link and logging it.
        # We don't return the link to the client for security/workflow reasons
        # (it's printed to logs for the developer).
        await auth_service.send_magic_link(request.email, base_url)

        return {"message": "Magic link generated. Check server logs."}
    except Exception as e:
        # Log the error and return 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/callback")
async def magic_callback(
    oobCode: str,
    email: str,
    auth_service: AuthService = Depends(get_auth_service_dependency),
):
    """
    Handle the magic link callback.
    Exchanges code for token and sets session cookie.
    """
    try:
        session_cookie = await auth_service.handle_callback(oobCode, email)

        # Determine if we are in production (Cloud Run) for cookie security
        is_production = os.getenv("K_SERVICE") is not None

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            key="session",
            value=session_cookie,
            httponly=True,
            secure=is_production,  # True in prod, False in dev (localhost)
            max_age=60 * 60 * 24 * 5,  # 5 days
            samesite="lax",
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication failed: {str(e)}",
        )


@dashboard_router.get("/dashboard")
async def dashboard(user: Dict = Depends(get_current_user)):
    """
    Protected dashboard endpoint.
    """
    return {
        "message": "Welcome, you are authenticated!",
        "email": user.get("email"),
        "uid": user.get("uid"),
    }
