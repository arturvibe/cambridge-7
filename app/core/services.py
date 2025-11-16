"""
Core application services and use cases.

This module contains the business logic, independent of
infrastructure details like HTTP or message queues.
"""

import logging
from typing import Dict

from app.core.domain import FrameIOEvent
from app.core.exceptions import PublisherError
from app.core.ports import EventPublisher

logger = logging.getLogger(__name__)


class FrameioWebhookService:
    """
    Application service for processing Frame.io webhooks.

    This is the core use case logic, independent of HTTP or infrastructure.
    """

    def __init__(self, event_publisher: EventPublisher):
        """
        Initialize the webhook service.

        Args:
            event_publisher: Publisher for distributing events
        """
        self.event_publisher = event_publisher

    def process_webhook(
        self,
        event: FrameIOEvent,
        headers: Dict[str, str],
        client_ip: str,
    ) -> str:
        """
        Process a Frame.io webhook event.

        This is the core business logic:
        1. Log the webhook event using structured logging.
        2. Publish event for downstream consumers.
        3. Enforce business rules (e.g., publishing must succeed).

        Args:
            event: Parsed Frame.io event domain model.
            headers: HTTP request headers.
            client_ip: Client IP address.

        Returns:
            Message ID from successful publication.

        Raises:
            PublisherError: If publishing fails or returns no message ID.
        """
        logger.info("frame.io webhook received")

        try:
            message_id = self.event_publisher.publish(event)
        except Exception as e:
            raise PublisherError(f"Failed to publish event: {e}") from e

        if not message_id:
            raise PublisherError("Publisher returned no message ID")

        logger.info(
            "Successfully published event",
            extra={"extra_fields": {"message_id": message_id}},
        )
        return message_id

    def shutdown(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            self.event_publisher.close()
            logger.info("Webhook service shut down successfully")
        except Exception as e:
            logger.warning(f"Error during webhook service shutdown: {e}")
