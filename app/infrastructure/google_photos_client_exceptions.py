class GooglePhotosClientError(Exception):
    """Base exception for Google Photos client errors."""

    pass


class GooglePhotosAuthError(GooglePhotosClientError):
    """Raised for errors related to authentication."""

    pass


class GooglePhotosUploadError(GooglePhotosClientError):
    """Raised for errors during the photo upload process."""

    pass
