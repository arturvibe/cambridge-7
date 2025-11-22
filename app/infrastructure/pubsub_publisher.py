"""
Google Cloud Pub/Sub event publisher implementation.

This is a driven adapter that implements the EventPublisher port
defined in the core domain.
"""

import asyncio
import json
import logging
import os
from typing import Optional

from google.api_core import exceptions
from google.cloud import pubsub_v1

from app.core.domain import FrameIOEvent

logger = logging.getLogger(__name__)


class GooglePubSubPublisher:
    """
    Concrete implementation of EventPublisher using Google Cloud Pub/Sub.

    Automatically detects and configures for:
    - Production: Uses GCP Pub/Sub service
    - Local development: Uses Pub/Sub emulator (via PUBSUB_EMULATOR_HOST)
    """

    def __init__(
        self, project_id: Optional[str] = None, topic_name: Optional[str] = None
    ):
        """
        Initialize Google Cloud Pub/Sub publisher.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            topic_name: Pub/Sub topic name (defaults to PUBSUB_TOPIC_NAME env var)
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.topic_name = topic_name or os.getenv("PUBSUB_TOPIC_NAME")

        # Check if using emulator
        self.emulator_host = os.getenv("PUBSUB_EMULATOR_HOST")

        if not self.project_id:
            raise ValueError("GCP_PROJECT_ID must be set for Pub/Sub publisher")

        if not self.topic_name:
            raise ValueError("PUBSUB_TOPIC_NAME must be set for Pub/Sub publisher")

        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)

        if self.emulator_host:
            logger.info(f"Using Pub/Sub emulator at {self.emulator_host}")
        else:
            logger.info(f"Pub/Sub publisher initialized for topic: {self.topic_path}")

    async def publish(self, event: FrameIOEvent) -> Optional[str]:
        """
        Publish a domain event to the Pub/Sub topic asynchronously.

        This is an infrastructure adapter - it handles serialization of the
        domain object to JSON for Pub/Sub. The core domain works with domain
        objects; this adapter translates them to infrastructure format.

        Uses asyncio.to_thread() to avoid blocking the event loop while waiting
        for the Pub/Sub publish to complete.

        Args:
            event: The domain event to publish

        Returns:
            Message ID if successful, None if failed
        """
        try:
            # Serialize domain object to JSON (infrastructure concern)
            message_data = event.to_dict()
            message_bytes = json.dumps(message_data, default=str).encode("utf-8")

            # Extract attributes from domain object (for Pub/Sub message metadata)
            attributes = {
                "event_type": event.event_type,
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
            }

            # Publish message (returns a future immediately)
            future = self.publisher.publish(
                self.topic_path, message_bytes, **attributes
            )

            # Wait for the result in a thread pool to avoid blocking the event loop
            message_id: str = await asyncio.to_thread(future.result, 10.0)
            logger.info(f"Published message to Pub/Sub: {message_id}")

            return message_id

        except exceptions.NotFound:
            logger.error(f"Pub/Sub topic not found: {self.topic_path}")
            return None
        except exceptions.PermissionDenied:
            logger.error(f"Permission denied publishing to topic: {self.topic_path}")
            return None
        except Exception as e:
            logger.error(f"Failed to publish message to Pub/Sub: {str(e)}")
            return None

    def close(self) -> None:
        """Close the publisher client."""
        if self.publisher:
            # Flush any pending messages
            self.publisher.stop()
