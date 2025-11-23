"""
Frame.io service integration.

Handles interaction with Frame.io API v2, including token refresh.
"""

import logging
from typing import Any, cast

import httpx

from app.oauth.config import get_oauth_config
from app.users.models import OAuthToken
from app.users.repository import UserRepository


logger = logging.getLogger(__name__)


class FrameioError(Exception):
    """Base exception for Frame.io errors."""

    pass


class FrameioAuthError(FrameioError):
    """Authentication/authorization error."""

    pass


class FrameioNotFoundError(FrameioError):
    """Resource not found."""

    pass


class FrameioRateLimitError(FrameioError):
    """Rate limit exceeded."""

    pass


class FrameioService:
    """Service for interacting with Frame.io API v2."""

    BASE_URL = "https://api.frame.io/v2"

    def __init__(self, token: OAuthToken, user_uid: str, repository: UserRepository):
        self._token = token
        self._user_uid = user_uid
        self._repository = repository
        self._config = get_oauth_config()

    async def refresh_token_if_needed(self) -> OAuthToken:
        """
        Refresh token if expired.

        Updates the token in the repository and the local instance.
        """
        if not self._token.is_expired():
            return self._token

        if not self._token.refresh_token:
            raise FrameioAuthError("Token expired and no refresh token available")

        logger.info(f"Refreshing Adobe token for user {self._user_uid}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://ims-na1.adobelogin.com/ims/token/v3",
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self._token.refresh_token,
                        "client_id": self._config.adobe_client_id,
                        "client_secret": self._config.adobe_client_secret,
                    },
                )

                if response.status_code == 400:
                    # Invalid refresh token or other client error
                    logger.error(f"Token refresh failed: {response.text}")
                    raise FrameioAuthError("Failed to refresh token (invalid grant)")

                response.raise_for_status()
                new_token_data = response.json()

                # Save to repository
                # Note: repo.save_token handles the full update logic
                new_token = await self._repository.save_token(
                    self._user_uid, "adobe", new_token_data
                )

                # Update local instance
                self._token = new_token
                return new_token

        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh token: {e.response.text}")
            raise FrameioAuthError(f"Failed to refresh token: {e}")
        except httpx.RequestError as e:
            logger.error(f"Network error refreshing token: {e}")
            raise FrameioError(f"Network error: {e}")

    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self._token.access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """
        Make a request to Frame.io API with automatic token refresh and error handling.
        """
        await self.refresh_token_if_needed()

        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        # Merge headers if provided
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)

                if response.status_code == 401:
                    raise FrameioAuthError("Unauthorized")
                elif response.status_code == 404:
                    raise FrameioNotFoundError("Resource not found")
                elif response.status_code == 429:
                    raise FrameioRateLimitError("Rate limit exceeded")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"Frame.io API error: {e.response.text}")
                raise FrameioError(f"API error: {e}")
            except httpx.RequestError as e:
                logger.error(f"Frame.io network error: {e}")
                raise FrameioError(f"Network error: {e}")

    async def get_me(self) -> dict:
        """Get current user info."""
        return cast(dict, await self._request("GET", "/me"))

    async def list_accounts(self) -> list[dict]:
        """List user's Frame.io accounts."""
        return cast(list[dict], await self._request("GET", "/accounts"))

    async def list_projects(self, account_id: str) -> list[dict]:
        """List projects in an account."""
        return cast(
            list[dict], await self._request("GET", f"/accounts/{account_id}/projects")
        )

    async def get_project(self, project_id: str) -> dict:
        """Get project details."""
        return cast(dict, await self._request("GET", f"/projects/{project_id}"))

    async def get_asset(self, asset_id: str) -> dict:
        """Get asset (file) details."""
        return cast(dict, await self._request("GET", f"/assets/{asset_id}"))

    async def list_assets(self, folder_id: str) -> list[dict]:
        """List assets in a folder."""
        return cast(
            list[dict], await self._request("GET", f"/assets/{folder_id}/children")
        )

    async def create_comment(
        self, asset_id: str, text: str, timestamp: float | None = None
    ) -> dict:
        """Create a comment on an asset."""
        body: dict[str, Any] = {"text": text}
        if timestamp is not None:
            body["timestamp"] = timestamp

        return cast(
            dict, await self._request("POST", f"/assets/{asset_id}/comments", json=body)
        )

    async def get_download_url(self, asset_id: str) -> str | None:
        """Get download URL for an asset."""
        asset = await self.get_asset(asset_id)
        return cast(str | None, asset.get("original"))

    async def create_upload_url(
        self, parent_id: str, filename: str, filesize: int
    ) -> dict:
        """Create upload URL for a new asset."""
        body = {
            "name": filename,
            "type": "file",
            "filesize": filesize,
        }
        return cast(
            dict,
            await self._request("POST", f"/assets/{parent_id}/children", json=body),
        )
