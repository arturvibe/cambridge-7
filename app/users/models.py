"""
User and OAuth token domain models.

These models represent the user identity and their connected OAuth services.
The User's Firebase UID (from magic link auth) is the primary key.
"""

from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OAuthToken(BaseModel):
    """
    OAuth2 token for a connected service.

    Stores the tokens received from OAuth providers (Google, Adobe, etc.).
    Tokens are associated with a user and provider.
    """

    provider: str = Field(description="OAuth provider name (google, adobe)")
    access_token: str = Field(description="OAuth2 access token")
    refresh_token: str | None = Field(
        default=None, description="OAuth2 refresh token for token renewal"
    )
    expires_at: int | None = Field(
        default=None, description="Token expiration timestamp (Unix epoch)"
    )
    token_type: str = Field(default="Bearer", description="Token type")
    scope: str | None = Field(default=None, description="Space-separated OAuth scopes")
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the service was connected",
    )

    model_config = ConfigDict(extra="allow")

    @classmethod
    def from_oauth_response(
        cls, provider: str, token_data: dict[str, Any]
    ) -> "OAuthToken":
        """
        Create OAuthToken from authlib token response.

        Args:
            provider: The OAuth provider name
            token_data: Raw token dict from authlib

        Returns:
            OAuthToken instance
        """
        return cls(
            provider=provider,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_at=token_data.get("expires_at"),
            token_type=token_data.get("token_type", "Bearer"),
            scope=token_data.get("scope"),
        )

    def to_authlib_token(self) -> dict[str, Any]:
        """
        Convert to dict format expected by authlib for token refresh.

        Returns:
            Dict compatible with authlib OAuth client
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "token_type": self.token_type,
            "scope": self.scope,
        }

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC).timestamp() >= self.expires_at


class User(BaseModel):
    """
    User domain model.

    The user's identity is established via magic link authentication.
    The Firebase UID serves as the primary key across all systems.
    Connected OAuth services are stored as a dict of provider -> token.
    """

    uid: str = Field(description="Firebase UID (primary key)")
    email: EmailStr = Field(description="User's email address")
    tokens: dict[str, OAuthToken] = Field(
        default_factory=dict,
        description="Connected OAuth tokens by provider",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Account creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    model_config = ConfigDict(extra="forbid")

    def get_token(self, provider: str) -> OAuthToken | None:
        """Get OAuth token for a specific provider."""
        return self.tokens.get(provider)

    def has_connection(self, provider: str) -> bool:
        """Check if user has connected a specific provider."""
        return provider in self.tokens

    def connected_providers(self) -> list[str]:
        """List all connected OAuth providers."""
        return list(self.tokens.keys())
