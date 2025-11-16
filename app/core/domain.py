"""
Core domain models for Frame.io webhook events.

These models represent the business domain and are independent of
any infrastructure or delivery mechanism.
"""

from typing import Any, Dict

from pydantic import AliasPath, BaseModel, Field


class FrameIOEvent(BaseModel):
    """
    Frame.io webhook event.

    Represents the complete webhook payload from Frame.io V4 API.
    Uses validation_alias to map nested JSON fields to flat Python fields.
    All fields are required.
    """

    # Map "type" from JSON to "event_type" in Python (avoid Python 'type' keyword)
    event_type: str = Field(
        validation_alias="type",
        description="Event type (e.g., file.created, file.ready)",
    )

    # Map nested fields from JSON to flat fields in Python
    resource_id: str = Field(
        validation_alias=AliasPath("resource", "id"),
        description="Resource ID from resource.id",
    )
    resource_type: str = Field(
        validation_alias=AliasPath("resource", "type"),
        description="Resource type from resource.type",
    )
    account_id: str = Field(
        validation_alias=AliasPath("account", "id"),
        description="Account ID from account.id",
    )
    workspace_id: str = Field(
        validation_alias=AliasPath("workspace", "id"),
        description="Workspace ID from workspace.id",
    )
    project_id: str = Field(
        validation_alias=AliasPath("project", "id"),
        description="Project ID from project.id",
    )
    user_id: str = Field(
        validation_alias=AliasPath("user", "id"),
        description="User ID from user.id",
    )

    class Config:
        # Populate by field name when serializing (use event_type, not type)
        populate_by_name = True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Reconstructs the nested JSON structure that Frame.io sends.
        This is important for Pub/Sub consumers who expect the original format.
        """
        return {
            "type": self.event_type,
            "resource": {
                "id": self.resource_id,
                "type": self.resource_type,
            },
            "account": {"id": self.account_id},
            "workspace": {"id": self.workspace_id},
            "project": {"id": self.project_id},
            "user": {"id": self.user_id},
        }
