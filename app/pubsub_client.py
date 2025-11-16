"""
Pub/Sub client for publishing Frame.io webhook events.
Supports both production (GCP) and local development (emulator).
"""

import json
import logging
import os
from typing import Dict, Any, Optional

from google.cloud import pubsub_v1
from google.api_core import exceptions

logger = logging.getLogger(__name__)


class PubSubClient:
    """
    Client for publishing messages to Google Cloud Pub/Sub.

    Automatically detects and configures for:
    - Production: Uses GCP Pub/Sub service
    - Local development: Uses Pub/Sub emulator (via PUBSUB_EMULATOR_HOST)
    """

    def __init__(self, project_id: Optional[str] = None, topic_name: Optional[str] = None):
        """
        Initialize Pub/Sub publisher client.

        Args:
            project_id: GCP project ID (defaults to GCP_PROJECT_ID env var)
            topic_name: Pub/Sub topic name (defaults to PUBSUB_TOPIC_NAME env var)
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.topic_name = topic_name or os.getenv("PUBSUB_TOPIC_NAME", "frameio-webhooks")
        self.enabled = os.getenv("PUBSUB_ENABLED", "true").lower() == "true"

        # Check if using emulator
        self.emulator_host = os.getenv("PUBSUB_EMULATOR_HOST")

        if not self.enabled:
            logger.info("Pub/Sub publishing is disabled (PUBSUB_ENABLED=false)")
            self.publisher = None
            self.topic_path = None
            return

        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set, Pub/Sub publishing disabled")
            self.enabled = False
            self.publisher = None
            self.topic_path = None
            return

        try:
            self.publisher = pubsub_v1.PublisherClient()
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)

            if self.emulator_host:
                logger.info(f"Using Pub/Sub emulator at {self.emulator_host}")
            else:
                logger.info(f"Pub/Sub publisher initialized for topic: {self.topic_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub client: {str(e)}")
            self.enabled = False
            self.publisher = None
            self.topic_path = None

    def publish(self, message_data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Publish a message to the Pub/Sub topic.

        Args:
            message_data: Dictionary containing the message payload
            attributes: Optional message attributes (metadata)

        Returns:
            Message ID if successful, None if failed or disabled
        """
        if not self.enabled or not self.publisher:
            logger.debug("Pub/Sub publishing skipped (disabled or not initialized)")
            return None

        try:
            # Convert message to JSON bytes
            message_bytes = json.dumps(message_data, default=str).encode("utf-8")

            # Add default attributes if not provided
            if attributes is None:
                attributes = {}

            # Publish message
            future = self.publisher.publish(
                self.topic_path,
                message_bytes,
                **attributes
            )

            # Wait for the publish to complete and get message ID
            message_id = future.result(timeout=5.0)
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

    def close(self):
        """Close the publisher client."""
        if self.publisher:
            # Flush any pending messages
            self.publisher.stop()
