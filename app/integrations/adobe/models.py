"""
Frame.io request and response models.

Pydantic models for Frame.io API interactions.
"""

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    """Request model for creating a comment on an asset."""

    text: str = Field(description="Comment text")
    timestamp: float | None = Field(
        default=None, description="Video timecode in seconds for video comments"
    )


class UploadRequest(BaseModel):
    """Request model for creating an upload URL."""

    filename: str = Field(description="Name of the file to upload")
    filesize: int = Field(description="Size of the file in bytes")


class AssetResponse(BaseModel):
    """Response model for Frame.io asset."""

    id: str = Field(description="Asset ID")
    name: str = Field(description="Asset name")
    type: str = Field(description="Asset type (file, folder, etc.)")
    filesize: int | None = Field(default=None, description="File size in bytes")
    original: str | None = Field(default=None, description="Download URL")

    model_config = ConfigDict(extra="allow")


class ProjectResponse(BaseModel):
    """Response model for Frame.io project."""

    id: str = Field(description="Project ID")
    name: str = Field(description="Project name")
    root_asset_id: str = Field(description="Root folder asset ID")

    model_config = ConfigDict(extra="allow")


class AccountResponse(BaseModel):
    """Response model for Frame.io account."""

    id: str = Field(description="Account ID")
    name: str = Field(description="Account name")

    model_config = ConfigDict(extra="allow")


class UserResponse(BaseModel):
    """Response model for Frame.io user."""

    id: str = Field(description="User ID")
    email: str = Field(description="User email")
    name: str | None = Field(default=None, description="User display name")

    model_config = ConfigDict(extra="allow")


class CommentResponse(BaseModel):
    """Response model for Frame.io comment."""

    id: str = Field(description="Comment ID")
    text: str = Field(description="Comment text")
    timestamp: float | None = Field(default=None, description="Video timecode")

    model_config = ConfigDict(extra="allow")


class DownloadUrlResponse(BaseModel):
    """Response model for download URL."""

    download_url: str | None = Field(description="Download URL for the asset")
