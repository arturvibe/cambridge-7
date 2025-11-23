"""
API router for Adobe Frame.io integration.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.users.repository import get_user_repository, UserRepository
from app.integrations.adobe.service import FrameioService
from app.integrations.adobe.models import CommentCreate

router = APIRouter(prefix="/integrations/adobe/frameio", tags=["frameio"])


async def get_frameio_service(
    user: dict[str, Any] = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> FrameioService:
    """Get FrameioService with user's token."""
    token = await repository.get_token(user["uid"], "adobe")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adobe account not connected. Visit /oauth/adobe/connect first.",
        )
    return FrameioService(token=token, user_uid=user["uid"], repository=repository)


@router.get("/me")
async def get_current_frameio_user(
    service: FrameioService = Depends(get_frameio_service),
) -> dict[str, Any]:
    """Get current Frame.io user info."""
    return await service.get_me()


@router.get("/accounts")
async def list_accounts(
    service: FrameioService = Depends(get_frameio_service),
) -> list[dict[str, Any]]:
    """List Frame.io accounts."""
    return await service.list_accounts()


@router.get("/accounts/{account_id}/projects")
async def list_projects(
    account_id: str,
    service: FrameioService = Depends(get_frameio_service),
) -> list[dict[str, Any]]:
    """List projects in an account."""
    return await service.list_projects(account_id)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    service: FrameioService = Depends(get_frameio_service),
) -> dict[str, Any]:
    """Get project details."""
    return await service.get_project(project_id)


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
) -> dict[str, Any]:
    """Get asset details."""
    return await service.get_asset(asset_id)


@router.get("/assets/{folder_id}/children")
async def list_assets(
    folder_id: str,
    service: FrameioService = Depends(get_frameio_service),
) -> list[dict[str, Any]]:
    """List assets in a folder."""
    return await service.list_assets(folder_id)


@router.post("/assets/{asset_id}/comments")
async def create_comment(
    asset_id: str,
    comment: CommentCreate,
    service: FrameioService = Depends(get_frameio_service),
) -> dict[str, Any]:
    """Create a comment on an asset."""
    return await service.create_comment(asset_id, comment.text, comment.timestamp)


@router.get("/assets/{asset_id}/download-url")
async def get_download_url(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
) -> dict[str, str | None]:
    """Get download URL for an asset."""
    url = await service.get_download_url(asset_id)
    return {"download_url": url}
