"""
Unit tests for the Frame.io API client.
"""
import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.infrastructure.frameio_client import FrameioSourceClient
from app.core.exceptions import FrameioClientError
from app.infrastructure.models import FrameioFile

# Constants for testing
TEST_TOKEN = "test_token"
TEST_ACCOUNT_ID = "account_123"
TEST_FILE_ID = "file_123"
BASE_URL = FrameioSourceClient.BASE_URL


@pytest.fixture
def client():
    """Provides a FrameioSourceClient instance."""
    return FrameioSourceClient()


def test_get_file_url_success(client):
    """Tests successful retrieval of the download URL and filename."""
    with patch("httpx.Client") as mock_http_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "name": "original.mp4",
                "media_links": {
                    "original": {"download_url": "https://example.com/original.mp4"}
                },
            }
        }
        mock_http_client.return_value.__enter__.return_value.get.return_value = mock_response

        frameio_file = client.get_file_url(
            token=TEST_TOKEN, account_id=TEST_ACCOUNT_ID, file_id=TEST_FILE_ID
        )

        assert isinstance(frameio_file, FrameioFile)
        assert frameio_file.url == "https://example.com/original.mp4"
        assert frameio_file.name == "original.mp4"
        mock_http_client.return_value.__enter__.return_value.get.assert_called_once_with(
            f"{BASE_URL}/accounts/{TEST_ACCOUNT_ID}/files/{TEST_FILE_ID}",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
            params={"include": "media_links.original"},
        )

def test_get_file_url_missing_url(client):
    """Tests that a FrameioClientError is raised when the URL is missing."""
    with patch("httpx.Client") as mock_http_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "name": "original.mp4",
                "media_links": {
                    "original": {}
                },
            }
        }
        mock_http_client.return_value.__enter__.return_value.get.return_value = mock_response

        with pytest.raises(FrameioClientError, match="Original download URL not found"):
            client.get_file_url(
                token=TEST_TOKEN, account_id=TEST_ACCOUNT_ID, file_id=TEST_FILE_ID
            )

def test_get_file_url_missing_filename(client):
    """Tests that a FrameioClientError is raised when the filename is missing."""
    with patch("httpx.Client") as mock_http_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "media_links": {
                    "original": {"download_url": "https://example.com/original.mp4"}
                },
            }
        }
        mock_http_client.return_value.__enter__.return_value.get.return_value = mock_response

        with pytest.raises(FrameioClientError, match="Original filename not found"):
            client.get_file_url(
                token=TEST_TOKEN, account_id=TEST_ACCOUNT_ID, file_id=TEST_FILE_ID
            )

def test_get_file_url_http_error(client):
    """Tests that a FrameioClientError is raised for HTTP errors."""
    with patch("httpx.Client") as mock_http_client:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_http_client.return_value.__enter__.return_value.get.return_value = mock_response

        with pytest.raises(FrameioClientError, match="API request failed"):
            client.get_file_url(
                token=TEST_TOKEN, account_id=TEST_ACCOUNT_ID, file_id=TEST_FILE_ID
            )

def test_get_file_url_network_error(client):
    """Tests that a FrameioClientError is raised for network errors."""
    with patch("httpx.Client") as mock_http_client:
        mock_http_client.return_value.__enter__.return_value.get.side_effect = httpx.RequestError(
            "Network error", request=MagicMock()
        )

        with pytest.raises(FrameioClientError, match="Network error"):
            client.get_file_url(
                token=TEST_TOKEN, account_id=TEST_ACCOUNT_ID, file_id=TEST_FILE_ID
            )
