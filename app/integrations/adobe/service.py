"""
Frame.io API service.

Service class for interacting with Frame.io API v2.
Handles authentication, token refresh, and API calls.
"""

import logging
from typing import Any

import httpx

from app.integrations.adobe.config import FrameioConfig, get_frameio_config
from app.integrations.adobe.exceptions import (
    FrameioAuthError,
    FrameioError,
    FrameioNotFoundError,
    FrameioRateLimitError,
    TokenExpiredError,
)
from app.users.models import OAuthToken


logger = logging.getLogger(__name__)


class FrameioService:
    """
    Service for interacting with Frame.io API v2.

    Uses stored OAuth tokens to authenticate API requests.
    Handles token refresh when tokens expire.
    """

    def __init__(
        self,
        token: OAuthToken,
        config: FrameioConfig | None = None,
        on_token_refresh: Any | None = None,
    ):
        """
        Initialize the Frame.io service.

        Args:
            token: OAuth token for authentication
            config: Frame.io configuration (uses default if not provided)
            on_token_refresh: Optional callback when token is refreshed.
                             Signature: async callback(new_token: OAuthToken) -> None
        """
        self._token = token
        self._config = config or get_frameio_config()
        self._on_token_refresh = on_token_refresh

    def _get_headers(self) -> dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self._token.access_token}",
            "Content-Type": "application/json",
        }

    async def _refresh_token_if_needed(self) -> None:
        """
        Refresh token if expired.

        Raises:
            TokenExpiredError: If token is expired and cannot be refreshed
        """
        if not self._token.is_expired():
            return

        if not self._token.refresh_token:
            raise TokenExpiredError("Token expired and no refresh token available")

        if not self._config.can_refresh_tokens():
            raise TokenExpiredError(
                "Token expired and client credentials not configured for refresh"
            )

        logger.info("Refreshing expired Adobe token")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self._config.token_refresh_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self._token.refresh_token,
                    "client_id": self._config.adobe_client_id,
                    "client_secret": self._config.adobe_client_secret,
                },
            )

            if response.status_code != 200:
                logger.error(f"Token refresh failed: {response.status_code}")
                raise TokenExpiredError(f"Token refresh failed: {response.status_code}")

            new_token_data = response.json()
            self._token = OAuthToken.from_oauth_response("adobe", new_token_data)

            # Notify callback if provided (for persisting refreshed token)
            if self._on_token_refresh:
                await self._on_token_refresh(self._token)

            logger.info("Adobe token refreshed successfully")

    def _handle_response_error(self, response: httpx.Response) -> None:
        """
        Handle HTTP error responses from Frame.io API.

        Args:
            response: HTTP response

        Raises:
            FrameioAuthError: For 401/403 errors
            FrameioNotFoundError: For 404 errors
            FrameioRateLimitError: For 429 errors
            FrameioError: For other errors
        """
        if response.status_code == 401:
            raise FrameioAuthError("Authentication failed - token may be invalid")
        if response.status_code == 403:
            raise FrameioAuthError("Access forbidden - insufficient permissions")
        if response.status_code == 404:
            raise FrameioNotFoundError("Resource not found")
        if response.status_code == 429:
            raise FrameioRateLimitError("Rate limit exceeded - try again later")
        if response.status_code >= 400:
            raise FrameioError(
                f"Frame.io API error: {response.status_code} - {response.text}"
            )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Make an authenticated request to Frame.io API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            json: Request body for POST/PUT requests

        Returns:
            Response JSON

        Raises:
            FrameioError: For API errors
        """
        await self._refresh_token_if_needed()

        url = f"{self._config.base_url}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json,
            )

            if response.status_code >= 400:
                self._handle_response_error(response)

            return response.json()

    async def get_me(self) -> dict[str, Any]:
        """
        Get current user info.

        Returns:
            User information from Frame.io
        """
        result = await self._make_request("GET", "/me")
        return result if isinstance(result, dict) else {}

    async def list_accounts(self) -> list[dict[str, Any]]:
        """
        List user's Frame.io accounts.

        Returns:
            List of accounts
        """
        result = await self._make_request("GET", "/accounts")
        return result if isinstance(result, list) else []

    async def list_projects(self, account_id: str) -> list[dict[str, Any]]:
        """
        List projects in an account.

        Args:
            account_id: Frame.io account ID

        Returns:
            List of projects
        """
        result = await self._make_request("GET", f"/accounts/{account_id}/projects")
        return result if isinstance(result, list) else []

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """
        Get project details.

        Args:
            project_id: Frame.io project ID

        Returns:
            Project details
        """
        result = await self._make_request("GET", f"/projects/{project_id}")
        return result if isinstance(result, dict) else {}

    async def get_asset(self, asset_id: str) -> dict[str, Any]:
        """
        Get asset (file/folder) details.

        Args:
            asset_id: Frame.io asset ID

        Returns:
            Asset details
        """
        result = await self._make_request("GET", f"/assets/{asset_id}")
        return result if isinstance(result, dict) else {}

    async def list_assets(self, folder_id: str) -> list[dict[str, Any]]:
        """
        List assets in a folder.

        Args:
            folder_id: Frame.io folder asset ID

        Returns:
            List of assets in the folder
        """
        result = await self._make_request("GET", f"/assets/{folder_id}/children")
        return result if isinstance(result, list) else []

    async def create_comment(
        self,
        asset_id: str,
        text: str,
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """
        Create a comment on an asset.

        Args:
            asset_id: Frame.io asset ID
            text: Comment text
            timestamp: Optional video timecode in seconds

        Returns:
            Created comment
        """
        body: dict[str, Any] = {"text": text}
        if timestamp is not None:
            body["timestamp"] = timestamp

        result = await self._make_request(
            "POST", f"/assets/{asset_id}/comments", json=body
        )
        return result if isinstance(result, dict) else {}

    async def get_download_url(self, asset_id: str) -> str | None:
        """
        Get download URL for an asset.

        Args:
            asset_id: Frame.io asset ID

        Returns:
            Download URL or None if not available
        """
        asset = await self.get_asset(asset_id)
        return asset.get("original")

    async def create_upload_url(
        self,
        parent_id: str,
        filename: str,
        filesize: int,
    ) -> dict[str, Any]:
        """
        Create upload URL for a new asset.

        Args:
            parent_id: Parent folder asset ID
            filename: Name of the file
            filesize: Size of the file in bytes

        Returns:
            Upload information including URL
        """
        result = await self._make_request(
            "POST",
            f"/assets/{parent_id}/children",
            json={
                "name": filename,
                "type": "file",
                "filesize": filesize,
            },
        )
        return result if isinstance(result, dict) else {}
