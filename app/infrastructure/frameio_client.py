"""
Client for interacting with the Frame.io API.
"""
import httpx
from pydantic import ValidationError

from app.core.domain import FrameioFile
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

    def get_file_url(self, token: str, account_id: str, file_id: str) -> FrameioFile:
        """
        Retrieves the original download URL for a given asset ID.

        Args:
            token: The API token for authentication.
            account_id: The ID of the account.
            file_id: The ID of the file.

        Returns:
            A FrameioFile object containing the URL and filename.

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
                response.raise_for_status()
                data = response.json()

            return FrameioFile.model_validate(data.get("data", {}))

        except ValidationError as e:
            raise FrameioClientError(f"Failed to parse API response for asset '{file_id}': {e}") from e
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
