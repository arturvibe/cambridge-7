"""
Unit tests for the Frame.io API client.
"""

import pytest
import httpx
from unittest.mock import patch, MagicMock

from app.infrastructure.frameio_client import FrameioSourceClient
from app.core.exceptions import FrameioClientError

# Constants for testing
TEST_TOKEN = "test_token"
TEST_ASSET_ID = "asset_123"
BASE_URL = FrameioSourceClient.BASE_URL


@pytest.fixture
def client():
    """Provides a FrameioSourceClient instance with a test token."""
    return FrameioSourceClient(token=TEST_TOKEN)


def test_client_initialization_success():
    """Tests successful client initialization."""
    client = FrameioSourceClient(token=TEST_TOKEN)
    assert client._headers["Authorization"] == f"Bearer {TEST_TOKEN}"


def test_client_initialization_empty_token():
    """Tests that client initialization fails with an empty token."""
    with pytest.raises(ValueError, match="API token cannot be empty."):
        FrameioSourceClient(token="")


@patch("httpx.Client")
def test_get_asset_original_download_url_success(mock_client, client):
    """Tests successful retrieval of the download URL."""
    # Mock the response from the API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "media_links": {"original": "https://example.com/original.mp4"}
    }
    mock_response.raise_for_status.return_value = None

    # Configure the mock client context manager
    mock_http_client = MagicMock()
    mock_http_client.get.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_http_client

    # Call the method and assert the result
    url = client.get_asset_original_download_url(asset_id=TEST_ASSET_ID)
    assert url == "https://example.com/original.mp4"
    mock_http_client.get.assert_called_once_with(
        f"{BASE_URL}/assets/{TEST_ASSET_ID}",
        headers={"Authorization": f"Bearer {TEST_TOKEN}"},
    )


@patch("httpx.Client")
def test_get_asset_original_download_url_missing_key(mock_client, client):
    """Tests handling of a response where the 'original' key is missing."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"media_links": {}}
    mock_response.raise_for_status.return_value = None

    mock_http_client = MagicMock()
    mock_http_client.get.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_http_client

    with pytest.raises(
        FrameioClientError,
        match=f"Original download URL not found for asset '{TEST_ASSET_ID}'.",
    ):
        client.get_asset_original_download_url(asset_id=TEST_ASSET_ID)


@patch("httpx.Client")
def test_get_asset_original_download_url_http_error(mock_client, client):
    """Tests handling of HTTP status errors (e.g., 404, 500)."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not Found", request=MagicMock(), response=mock_response
    )

    mock_http_client = MagicMock()
    mock_http_client.get.return_value = mock_response
    mock_client.return_value.__enter__.return_value = mock_http_client

    with pytest.raises(
        FrameioClientError,
        match=f"API request failed for asset '{TEST_ASSET_ID}': 404 Not Found",
    ):
        client.get_asset_original_download_url(asset_id=TEST_ASSET_ID)


@patch("httpx.Client")
def test_get_asset_original_download_url_network_error(mock_client, client):
    """Tests handling of network request errors."""
    mock_http_client = MagicMock()
    mock_http_client.get.side_effect = httpx.RequestError(
        "Network error", request=MagicMock()
    )
    mock_client.return_value.__enter__.return_value = mock_http_client

    with pytest.raises(
        FrameioClientError,
        match=f"Network error while fetching asset '{TEST_ASSET_ID}':",
    ):
        client.get_asset_original_download_url(asset_id=TEST_ASSET_ID)
