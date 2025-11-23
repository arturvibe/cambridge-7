"""
Frame.io API router.

API endpoints for Frame.io operations.
Requires authenticated user with connected Adobe account.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.integrations.adobe.exceptions import (
    FrameioAuthError,
    FrameioError,
    FrameioNotFoundError,
    FrameioRateLimitError,
)
from app.integrations.adobe.models import CommentCreate, DownloadUrlResponse
from app.integrations.adobe.service import FrameioService
from app.users.models import OAuthToken
from app.users.repository import UserRepository, get_user_repository


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations/adobe/frameio", tags=["frameio"])


async def get_frameio_service(
    user: dict = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> FrameioService:
    """
    Get FrameioService with user's token.

    Dependency that creates a FrameioService instance with the
    authenticated user's Adobe OAuth token.

    Args:
        user: Current authenticated user from session
        repository: User repository for token lookup

    Returns:
        Configured FrameioService

    Raises:
        HTTPException: 403 if Adobe account not connected
    """
    uid = user.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in session",
        )

    token = await repository.get_token(uid, "adobe")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adobe account not connected. Visit /oauth/adobe/connect first.",
        )

    # Create callback for persisting refreshed tokens
    async def on_token_refresh(new_token: OAuthToken) -> None:
        await repository.save_token(uid, "adobe", new_token.to_authlib_token())
        logger.info(f"Persisted refreshed Adobe token for user {uid}")

    return FrameioService(token, on_token_refresh=on_token_refresh)


def handle_frameio_error(e: FrameioError) -> HTTPException:
    """Convert Frame.io exceptions to HTTP exceptions."""
    if isinstance(e, FrameioAuthError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    if isinstance(e, FrameioNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    if isinstance(e, FrameioRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e),
        )
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Frame.io API error: {str(e)}",
    )


@router.get("/me")
async def get_current_frameio_user(
    service: FrameioService = Depends(get_frameio_service),
):
    """
    Get current Frame.io user info.

    Returns the Frame.io user profile associated with the connected
    Adobe account.
    """
    try:
        return await service.get_me()
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/accounts")
async def list_accounts(
    service: FrameioService = Depends(get_frameio_service),
):
    """
    List Frame.io accounts.

    Returns all Frame.io accounts the user has access to.
    """
    try:
        return await service.list_accounts()
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/accounts/{account_id}/projects")
async def list_projects(
    account_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    List projects in an account.

    Args:
        account_id: Frame.io account ID
    """
    try:
        return await service.list_projects(account_id)
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    Get project details.

    Args:
        project_id: Frame.io project ID
    """
    try:
        return await service.get_project(project_id)
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    Get asset details.

    Args:
        asset_id: Frame.io asset ID
    """
    try:
        return await service.get_asset(asset_id)
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/assets/{folder_id}/children")
async def list_assets(
    folder_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    List assets in a folder.

    Args:
        folder_id: Frame.io folder asset ID
    """
    try:
        return await service.list_assets(folder_id)
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.post("/assets/{asset_id}/comments")
async def create_comment(
    asset_id: str,
    comment: CommentCreate,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    Create a comment on an asset.

    Args:
        asset_id: Frame.io asset ID
        comment: Comment data including text and optional timestamp
    """
    try:
        return await service.create_comment(asset_id, comment.text, comment.timestamp)
    except FrameioError as e:
        raise handle_frameio_error(e)


@router.get("/assets/{asset_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """
    Get download URL for an asset.

    Args:
        asset_id: Frame.io asset ID

    Returns:
        Object containing the download URL
    """
    try:
        url = await service.get_download_url(asset_id)
        return DownloadUrlResponse(download_url=url)
    except FrameioError as e:
        raise handle_frameio_error(e)
