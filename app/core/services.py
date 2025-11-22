"""
Core application services and use cases.

This module contains the business logic, independent of
infrastructure details like HTTP or message queues.
"""

import json
import logging
from datetime import UTC, datetime
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

    async def process_webhook(
        self,
        event: FrameIOEvent,
        headers: Dict[str, str],
        client_ip: str,
    ) -> str:
        """
        Process a Frame.io webhook event asynchronously.

        This is the core business logic:
        1. Log the webhook event (structured JSON for Cloud Logging)
        2. Publish event for downstream consumers
        3. Enforce business rules (publishing must succeed)

        Args:
            event: Parsed Frame.io event domain model
            headers: HTTP request headers
            client_ip: Client IP address

        Returns:
            Message ID from successful publication

        Raises:
            PublisherError: If publishing fails or returns no message ID
        """
        # Log webhook data as structured JSON for Cloud Logging
        # Single log entry with jsonPayload and automatic trace correlation
        log_data = {
            "message": "FRAME.IO WEBHOOK RECEIVED",
            "event_type": event.event_type,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "account_id": event.account_id,
            "workspace_id": event.workspace_id,
            "project_id": event.project_id,
            "user_id": event.user_id,
            "user_agent": headers.get("user-agent", ""),
            "timestamp": datetime.now(UTC).isoformat(),
            "client_ip": client_ip,
            "headers": headers,
            "payload": event.to_dict(),
        }
        logger.info(json.dumps(log_data, default=str))

        # Publish event to downstream consumers
        # Pass the domain object - infrastructure layer handles serialization
        try:
            message_id = await self.event_publisher.publish(event)
        except Exception as e:
            # Publishing failed - raise domain exception
            raise PublisherError(f"Failed to publish event: {str(e)}") from e

        # Enforce business rule: publishing must return a message ID
        if not message_id:
            raise PublisherError("Publisher returned no message ID")

        logger.info(f"Published event with message ID: {message_id}")
        return message_id

    def shutdown(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            self.event_publisher.close()
            logger.info("Webhook service shut down successfully")
        except Exception as e:
            logger.warning(f"Error during webhook service shutdown: {e}")
