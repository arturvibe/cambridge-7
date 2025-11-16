"""
Core application services and use cases.

This module contains the business logic, independent of
infrastructure details like HTTP or message queues.
"""

import logging
from typing import Optional

from app.core.domain import FrameIOEvent
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

    def process_webhook(self, event: FrameIOEvent) -> Optional[str]:
        """
        Process a Frame.io webhook event.

        This is the core business logic:
        1. Publish event for downstream consumers
        2. Return message ID if successful

        Args:
            event: Parsed Frame.io event domain model

        Returns:
            Message ID if published successfully, None otherwise
        """
        logger.info(
            f"Processing Frame.io event: {event.event_type} "
            f"for resource {event.resource_type}:{event.resource_id}"
        )

        # Publish event to downstream consumers
        try:
            message_id = self.event_publisher.publish(
                message_data=event.to_dict(),
                attributes={
                    "event_type": event.event_type,
                    "resource_type": event.resource_type,
                    "resource_id": event.resource_id,
                },
            )
            if message_id:
                logger.info(f"Published event with message ID: {message_id}")
            return message_id
        except Exception as e:
            # Don't fail the webhook if publishing fails
            logger.error(f"Failed to publish event: {str(e)}", exc_info=True)
            return None

    def shutdown(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            self.event_publisher.close()
            logger.info("Webhook service shut down successfully")
        except Exception as e:
            logger.warning(f"Error during webhook service shutdown: {e}")
