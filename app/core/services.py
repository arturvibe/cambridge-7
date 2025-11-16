"""
Core application services and use cases.

This module contains the business logic, independent of
infrastructure details like HTTP or message queues.
"""

import logging
from typing import Any, Dict, Optional, Protocol

from app.core.domain import FrameIOEvent

logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    """
    Port (interface) for publishing events.

    This is implemented by infrastructure adapters (e.g., GooglePubSubPublisher).
    The core domain depends on this interface, not on concrete implementations.
    """

    def publish(
        self, message_data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Publish an event message.

        Args:
            message_data: The event data to publish
            attributes: Optional metadata attributes

        Returns:
            Message ID if successful, None otherwise
        """
        ...

    def close(self) -> None:
        """Close the publisher and cleanup resources."""
        ...


class WebhookService:
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
        self, payload: Dict[str, Any], metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process a Frame.io webhook event.

        This is the core business logic:
        1. Parse and validate the payload
        2. Create domain model
        3. Publish event for downstream consumers
        4. Return processing result

        Args:
            payload: Raw webhook payload
            metadata: Optional metadata (headers, IP, etc.)

        Returns:
            Processing result with status and message ID
        """
        try:
            # Parse into domain model (Pydantic handles nested field extraction via validation_alias)
            event = FrameIOEvent(**payload)

            logger.info(
                f"Processing Frame.io event: {event.event_type} "
                f"for resource {event.resource_type}:{event.resource_id}"
            )

            # Publish event to downstream consumers
            message_id = None
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
            except Exception as e:
                # Don't fail the webhook if publishing fails
                logger.error(f"Failed to publish event: {str(e)}", exc_info=True)

            # Return processing result
            result = {
                "status": "received",
                "event_type": event.event_type,
                "resource_type": event.resource_type,
            }

            if message_id:
                result["pubsub_message_id"] = message_id

            return result

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            raise

    def shutdown(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            self.event_publisher.close()
            logger.info("Webhook service shut down successfully")
        except Exception as e:
            logger.warning(f"Error during webhook service shutdown: {e}")
