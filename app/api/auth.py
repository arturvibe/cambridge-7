"""
API endpoints for OAuth 2.0 authorization flows.
"""

import logging
from fastapi import APIRouter, Depends, Request
from app.core.oauth_service import OAuthService

router = APIRouter()
logger = logging.getLogger(__name__)


# This is a placeholder that will be overridden in app/main.py
def get_oauth_service_dependency() -> OAuthService:
    raise NotImplementedError("This dependency should be overridden")


@router.get("/connect/adobe")
async def login_adobe(
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service_dependency),
):
    redirect_uri = request.url_for("auth_adobe")
    return await oauth_service.login(request, redirect_uri)


@router.get("/auth/adobe")
async def auth_adobe(
    request: Request,
    oauth_service: OAuthService = Depends(get_oauth_service_dependency),
):
    token = await oauth_service.auth(request)
    logger.info(f"Adobe Access Token: {token.get('access_token')}")
    logger.info(f"Adobe Refresh Token: {token.get('refresh_token')}")
    return {"message": "Successfully authorized with Adobe."}
