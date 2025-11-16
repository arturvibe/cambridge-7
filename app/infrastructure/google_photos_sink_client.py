import logging
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from app.infrastructure.google_photos_client_exceptions import (
    GooglePhotosAuthError,
    GooglePhotosUploadError,
)

logger = logging.getLogger(__name__)


class GooglePhotosSinkClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token

    def _get_gphotos_service(self):
        try:
            creds = Credentials(
                None,
                refresh_token=self._refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_id,
                client_secret=self._client_secret,
            )
            logger.info("Refreshing access token for Google Photos...")
            creds.refresh(Request())
            service = build(
                "photoslibrary", "v1", credentials=creds, static_discovery=False
            )
            logger.info("Google Photos service initialized successfully.")
            return service, creds
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise GooglePhotosAuthError(
                "Failed to refresh Google Photos access token."
            ) from e

    def upload_photo(self, photo_bytes: bytes, file_name: str, description: str):
        service, creds = self._get_gphotos_service()

        # Step 1: Upload bytes for an upload_token
        upload_url = "https://photoslibrary.googleapis.com/v1/uploads"
        headers = {
            "Authorization": "Bearer " + creds.token,
            "Content-Type": "application/octet-stream",
            "X-Goog-Upload-Protocol": "raw",
        }
        try:
            logger.info(f"Uploading {len(photo_bytes)} bytes to get upload_token...")
            response = requests.post(upload_url, data=photo_bytes, headers=headers)
            response.raise_for_status()
            upload_token = response.text
            logger.info(f"Got upload_token: {upload_token}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during byte upload: {e}")
            raise GooglePhotosUploadError("Failed to upload photo bytes.") from e

        # Step 2: Create media item with the token
        try:
            logger.info("Creating media item in Google Photos library...")
            body = {
                "newMediaItems": [
                    {
                        "description": description,
                        "simpleMediaItem": {
                            "uploadToken": upload_token,
                            "fileName": file_name,
                        },
                    }
                ]
            }
            result = service.mediaItems().batchCreate(body=body).execute()

            status = result["newMediaItemResults"][0]["status"]
            if status["message"] == "Success":
                media_item = result["newMediaItemResults"][0]["mediaItem"]
                logger.info(f"Successfully uploaded photo: {media_item['productUrl']}")
                return media_item
            else:
                logger.error(f"Error creating media item: {status['message']}")
                raise GooglePhotosUploadError(
                    f"API failed to create media item: {status['message']}"
                )

        except HttpError as e:
            logger.error(f"HttpError creating media item: {e}")
            raise GooglePhotosUploadError(
                "An HTTP error occurred while creating the media item."
            ) from e
        except Exception as e:
            logger.error(f"An unexpected error occurred creating the media item: {e}")
            raise GooglePhotosUploadError("An unexpected error occurred.") from e
