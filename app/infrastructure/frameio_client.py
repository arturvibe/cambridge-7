"""
Client for interacting with the Frame.io API.
"""
from typing import Tuple
import httpx

from app.core.exceptions import FrameioClientError


class FrameioSourceClient:
    """
    A client for retrieving asset source URLs from the Frame.io API.
    """

    BASE_URL = "https://api.frame.io/v4"

    def __init__(self):
        """
        Initializes the client.
        """
        pass

    def get_file_url(self, token: str, account_id: str, file_id: str) -> Tuple[str, str]:
        """
        Retrieves the original download URL for a given asset ID.

        Args:
            token: The API token for authentication.
            account_id: The ID of the account.
            file_id: The ID of the file.

        Returns:
            A tuple containing the original download URL and the original filename.

        Raises:
            FrameioClientError: If the API call fails or the URL is not found.
        """
        url = f"{self.BASE_URL}/accounts/{account_id}/files/{file_id}"
        params = {"include": "media_links.original"}
        headers = {
            "Authorization": f"Bearer {token}",
        }
        try:
            with httpx.Client() as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx
                data = response.json()

            # The v4 API nests the asset data under a 'data' key
            asset_data = data.get("data", {})
            original_url = asset_data.get("media_links", {}).get("original", {}).get("download_url")
            original_filename = asset_data.get("name")

            if not original_url:
                raise FrameioClientError(
                    f"Original download URL not found for asset '{file_id}'."
                )
            if not original_filename:
                raise FrameioClientError(
                    f"Original filename not found for asset '{file_id}'."
                )

            return original_url, original_filename

        except httpx.HTTPStatusError as e:
            raise FrameioClientError(
                f"API request failed for asset '{file_id}': {e.response.status_code} {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise FrameioClientError(
                f"Network error while fetching asset '{file_id}': {e}"
            ) from e
        except Exception as e:
            raise FrameioClientError(
                f"An unexpected error occurred for asset '{file_id}': {e}"
            ) from e
