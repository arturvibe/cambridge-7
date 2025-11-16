"""
Client for interacting with the Frame.io API.
"""

import httpx

from app.core.exceptions import FrameioClientError


class FrameioSourceClient:
    """
    A client for retrieving asset source URLs from the Frame.io API.
    """

    BASE_URL = "https://api.frame.io/v2"

    def __init__(self, token: str):
        """
        Initializes the client with a Frame.io API token.

        Args:
            token: The API token for authentication.
        """
        if not token:
            raise ValueError("API token cannot be empty.")
        self._headers = {
            "Authorization": f"Bearer {token}",
        }

    def get_asset_original_download_url(self, asset_id: str) -> str:
        """
        Retrieves the original download URL for a given asset ID.

        Args:
            asset_id: The ID of the asset.

        Returns:
            The original download URL for the asset.

        Raises:
            FrameioClientError: If the API call fails or the URL is not found.
        """
        url = f"{self.BASE_URL}/assets/{asset_id}"
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=self._headers)
                response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
                data = response.json()

            original_url = data.get("media_links", {}).get("original")
            if not original_url:
                raise FrameioClientError(f"Original download URL not found for asset '{asset_id}'.")

            return original_url

        except httpx.HTTPStatusError as e:
            raise FrameioClientError(f"API request failed for asset '{asset_id}': {e.response.status_code} {e.response.text}") from e
        except httpx.RequestError as e:
            raise FrameioClientError(f"Network error while fetching asset '{asset_id}': {e}") from e
        except Exception as e:
            raise FrameioClientError(f"An unexpected error occurred for asset '{asset_id}': {e}") from e
