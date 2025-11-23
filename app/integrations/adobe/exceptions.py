"""
Frame.io integration exceptions.

Custom exceptions for Frame.io API errors.
"""


class FrameioError(Exception):
    """Base exception for Frame.io errors."""

    pass


class FrameioAuthError(FrameioError):
    """Authentication/authorization error (401/403)."""

    pass


class FrameioNotFoundError(FrameioError):
    """Resource not found (404)."""

    pass


class FrameioRateLimitError(FrameioError):
    """Rate limit exceeded (429)."""

    pass


class TokenExpiredError(FrameioAuthError):
    """Token expired and cannot be refreshed."""

    pass
