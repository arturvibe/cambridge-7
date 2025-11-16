import pytest
import requests
from unittest.mock import patch, MagicMock
from app.infrastructure.google_photos_sink_client import GooglePhotosSinkClient
from app.infrastructure.google_photos_client_exceptions import (
    GooglePhotosAuthError,
    GooglePhotosUploadError,
)

@pytest.fixture
def mock_credentials():
    """Fixture for mock Google credentials."""
    mock_creds = MagicMock()
    mock_creds.token = "mock_access_token"
    return mock_creds

@pytest.fixture
def mock_gphotos_service():
    """Fixture for a mock Google Photos service object."""
    return MagicMock()

@patch("app.infrastructure.google_photos_sink_client.build")
@patch("app.infrastructure.google_photos_sink_client.Request")
@patch("app.infrastructure.google_photos_sink_client.Credentials")
def test_get_gphotos_service_success(
    mock_creds_class, mock_request, mock_build, mock_credentials
):
    """Test successful Google Photos service initialization."""
    mock_creds_class.return_value = mock_credentials
    mock_build.return_value = MagicMock()

    client = GooglePhotosSinkClient("id", "secret", "refresh")
    service, creds = client._get_gphotos_service()

    assert service is not None
    assert creds is not None
    mock_credentials.refresh.assert_called_once()


@patch(
    "app.infrastructure.google_photos_sink_client.Credentials",
    side_effect=Exception("Auth error"),
)
def test_get_gphotos_service_auth_error(mock_creds_class):
    """Test that GooglePhotosAuthError is raised on auth failure."""
    client = GooglePhotosSinkClient("id", "secret", "refresh")
    with pytest.raises(GooglePhotosAuthError):
        client._get_gphotos_service()


@patch("app.infrastructure.google_photos_sink_client.GooglePhotosSinkClient._get_gphotos_service")
@patch("requests.post")
def test_upload_photo_success(
    mock_post, mock_get_service, mock_gphotos_service, mock_credentials
):
    """Test a successful photo upload."""
    mock_get_service.return_value = (mock_gphotos_service, mock_credentials)

    # Mock the response from the byte upload
    mock_upload_response = MagicMock()
    mock_upload_response.raise_for_status.return_value = None
    mock_upload_response.text = "mock_upload_token"
    mock_post.return_value = mock_upload_response

    # Mock the response from the media item creation
    mock_create_response = {
        "newMediaItemResults": [
            {
                "status": {"message": "Success"},
                "mediaItem": {"id": "mock_id", "productUrl": "mock_url"},
            }
        ]
    }
    mock_gphotos_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = mock_create_response

    client = GooglePhotosSinkClient("id", "secret", "refresh")
    result = client.upload_photo(b"test_bytes", "test.jpg", "A test photo")

    assert result["id"] == "mock_id"
    mock_post.assert_called_once()
    mock_gphotos_service.mediaItems().batchCreate.assert_called_once()

@patch("app.infrastructure.google_photos_sink_client.GooglePhotosSinkClient._get_gphotos_service")
@patch("requests.post", side_effect=requests.exceptions.RequestException("Network error"))
def test_upload_photo_upload_error(
    mock_post, mock_get_service, mock_gphotos_service, mock_credentials
):
    """Test that GooglePhotosUploadError is raised on byte upload failure."""
    mock_get_service.return_value = (mock_gphotos_service, mock_credentials)

    client = GooglePhotosSinkClient("id", "secret", "refresh")
    with pytest.raises(GooglePhotosUploadError):
        client.upload_photo(b"test_bytes", "test.jpg", "A test photo")

@patch("app.infrastructure.google_photos_sink_client.GooglePhotosSinkClient._get_gphotos_service")
@patch("requests.post")
def test_upload_photo_media_item_creation_error(
    mock_post, mock_get_service, mock_gphotos_service, mock_credentials
):
    """Test that GooglePhotosUploadError is raised on media item creation failure."""
    mock_get_service.return_value = (mock_gphotos_service, mock_credentials)

    mock_upload_response = MagicMock()
    mock_upload_response.raise_for_status.return_value = None
    mock_upload_response.text = "mock_upload_token"
    mock_post.return_value = mock_upload_response

    mock_create_response = {
        "newMediaItemResults": [{"status": {"message": "API Error"}}]
    }
    mock_gphotos_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = mock_create_response

    client = GooglePhotosSinkClient("id", "secret", "refresh")
    with pytest.raises(GooglePhotosUploadError):
        client.upload_photo(b"test_bytes", "test.jpg", "A test photo")
