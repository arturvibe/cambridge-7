"""
Core domain models for Frame.io webhook events.

These models represent the business domain and are independent of
any infrastructure or delivery mechanism.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class FrameIOResource(BaseModel):
    """Frame.io resource within an event."""

    type: str = Field(
        default="unknown", description="Resource type (e.g., file, asset)"
    )
    id: str = Field(default="unknown", description="Resource ID")
    name: Optional[str] = Field(default=None, description="Resource name")

    class Config:
        extra = "allow"  # Allow additional fields


class FrameIOAccount(BaseModel):
    """Frame.io account information."""

    id: Optional[str] = Field(default=None, description="Account ID")

    class Config:
        extra = "allow"


class FrameIOWorkspace(BaseModel):
    """Frame.io workspace information."""

    id: Optional[str] = Field(default=None, description="Workspace ID")

    class Config:
        extra = "allow"


class FrameIOProject(BaseModel):
    """Frame.io project information."""

    id: Optional[str] = Field(default=None, description="Project ID")

    class Config:
        extra = "allow"


class FrameIOUser(BaseModel):
    """Frame.io user information."""

    id: Optional[str] = Field(default=None, description="User ID")

    class Config:
        extra = "allow"


class FrameIOEvent(BaseModel):
    """
    Frame.io webhook event.

    Represents the complete webhook payload from Frame.io V4 API.
    """

    type: str = Field(description="Event type (e.g., file.created, file.ready)")
    resource: FrameIOResource = Field(default_factory=lambda: FrameIOResource())
    account: FrameIOAccount = Field(default_factory=lambda: FrameIOAccount())
    workspace: FrameIOWorkspace = Field(default_factory=lambda: FrameIOWorkspace())
    project: FrameIOProject = Field(default_factory=lambda: FrameIOProject())
    user: FrameIOUser = Field(default_factory=lambda: FrameIOUser())

    class Config:
        extra = "allow"  # Allow additional fields not in the model

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return self.type

    @property
    def resource_type(self) -> str:
        """Get the resource type."""
        return self.resource.type

    @property
    def resource_id(self) -> str:
        """Get the resource ID."""
        return self.resource.id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return self.model_dump(mode="json")
