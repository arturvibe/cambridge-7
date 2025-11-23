"""
Domain exceptions for the core business logic.

These exceptions represent business rule violations and are caught
by centralized exception handlers in main.py.
"""


class PublisherError(Exception):
    """
    Raised when event publishing fails.

    This indicates a server-side error (Pub/Sub unavailable, network issue, etc.)
    and should result in a 500 response so the client can retry.
    """

    pass


class FrameioClientError(Exception):
    """Raised for errors interacting with the Frame.io API."""

    pass


class InvalidWebhookError(Exception):
    """
    Raised when webhook event fails business validation.

    This indicates a client-side error (invalid event structure, missing data, etc.)
    and should result in a 4xx response.
    """

    pass
