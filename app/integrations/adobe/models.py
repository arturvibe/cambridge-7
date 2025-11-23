"""
Pydantic models for Adobe Frame.io integration.
"""

from pydantic import BaseModel


class CommentCreate(BaseModel):
    """Request model for creating a comment."""

    text: str
    timestamp: float | None = None  # For video timecode comments


class AssetResponse(BaseModel):
    """Response model for an asset (file/folder)."""

    id: str
    name: str
    type: str
    filesize: int | None = None
    original: str | None = None  # Download URL


class ProjectResponse(BaseModel):
    """Response model for a project."""

    id: str
    name: str
    root_asset_id: str
