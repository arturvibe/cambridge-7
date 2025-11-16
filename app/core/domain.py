"""
Core domain models for Frame.io webhook events.

These models represent the business domain and are independent of
any infrastructure or delivery mechanism.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class FrameIOEvent(BaseModel):
    """
    Frame.io webhook event.

    Represents the complete webhook payload from Frame.io V4 API.
    Flattened structure extracting IDs from nested objects.
    """

    type: str = Field(description="Event type (e.g., file.created, file.ready)")
    resource_id: str = Field(
        default="unknown", description="Resource ID from resource.id"
    )
    resource_type: str = Field(
        default="unknown", description="Resource type from resource.type"
    )
    account_id: Optional[str] = Field(default=None, description="Account ID")
    workspace_id: Optional[str] = Field(default=None, description="Workspace ID")
    project_id: Optional[str] = Field(default=None, description="Project ID")
    user_id: Optional[str] = Field(default=None, description="User ID")

    # Store the original payload for full context (not part of serialization)
    raw_payload: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    class Config:
        extra = "allow"  # Allow additional fields not in the model

    @field_validator("type", mode="before")
    @classmethod
    def validate_type(cls, v):
        """Ensure type is present."""
        if not v:
            return "unknown"
        return v

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "FrameIOEvent":
        """
        Create FrameIOEvent from raw webhook payload.

        Extracts IDs from nested objects while preserving the original payload.

        Args:
            payload: Raw webhook payload with nested structure

        Returns:
            FrameIOEvent with flattened structure
        """
        # Extract nested values
        resource = payload.get("resource", {})
        account = payload.get("account", {})
        workspace = payload.get("workspace", {})
        project = payload.get("project", {})
        user = payload.get("user", {})

        event = cls(
            type=payload.get("type", "unknown"),
            resource_id=resource.get("id", "unknown"),
            resource_type=resource.get("type", "unknown"),
            account_id=account.get("id"),
            workspace_id=workspace.get("id"),
            project_id=project.get("id"),
            user_id=user.get("id"),
        )

        # Store original payload
        event.raw_payload = payload

        return event

    @property
    def event_type(self) -> str:
        """Get the event type."""
        return self.type

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns the original payload if available, otherwise the flattened model.
        """
        if self.raw_payload:
            return self.raw_payload
        return self.model_dump(mode="json")
