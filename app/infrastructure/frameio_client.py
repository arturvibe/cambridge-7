"""
Frame.io API client for source operations.
"""

import httpx
from pydantic import ValidationError

from app.core.domain import FrameioFile
from app.core.exceptions import FrameioClientError


class FrameioSourceClient:
    """
    Client for interacting with the Frame.io API (V4).

    This client is responsible for source-side operations, such as
    retrieving file information and download URLs.
    """

    def __init__(self, base_url: str = "https://api.frame.io"):
        """
        Initialize the client.

        Args:
            base_url: The base URL for the Frame.io API.
        """
        self.base_url = base_url

    async def get_file_url(
        self,
        token: str,
        account_id: str,
        file_id: str,
    ) -> FrameioFile:
        """
        Get the download URL for a file from the Frame.io API.

        Args:
            token: The Frame.io API token.
            account_id: The ID of the account.
            file_id: The ID of the file.

        Returns:
            A FrameioFile object with the file's name and download URL.

        Raises:
            FrameioClientError: If the API call fails or the response is invalid.
        """
        api_url = f"{self.base_url}/v4/accounts/{account_id}/files/{file_id}"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"include": "media_links.original"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(api_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                return FrameioFile.model_validate(data)
            except httpx.HTTPStatusError as e:
                raise FrameioClientError(f"API request failed: {e}") from e
            except httpx.RequestError as e:
                raise FrameioClientError(f"Network error: {e}") from e
            except ValidationError as e:
                raise FrameioClientError(f"Invalid API response: {e}") from e
