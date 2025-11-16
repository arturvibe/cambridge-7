"""
Unit tests for the GooglePubSubPublisher infrastructure adapter.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions

from app.infrastructure.pubsub_publisher import GooglePubSubPublisher


class TestGooglePubSubPublisher:
    """Test Google Pub/Sub publisher initialization."""

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publisher_initialization(self, mock_publisher_class):
        """Test publisher initializes correctly."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher(topic_name="test-topic")

            assert publisher.project_id == "test-project"
            assert publisher.topic_name == "test-topic"
            mock_publisher_class.assert_called_once()

    def test_publisher_missing_project_id_raises_error(self):
        """Test publisher raises error when project ID is missing."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="GCP_PROJECT_ID must be set"):
                GooglePubSubPublisher()

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publisher_detects_emulator(self, mock_publisher_class):
        """Test publisher detects Pub/Sub emulator."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        with patch.dict(
            os.environ,
            {
                "GCP_PROJECT_ID": "test-project",
                "PUBSUB_EMULATOR_HOST": "localhost:8085",
            },
        ):
            publisher = GooglePubSubPublisher()

            assert publisher.emulator_host == "localhost:8085"

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publisher_default_topic_name(self, mock_publisher_class):
        """Test publisher uses default topic name."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/frameio-events"
        )

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            assert publisher.topic_name == "frameio-events"


class TestGooglePubSubPublish:
    """Test publishing messages to Pub/Sub."""

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publish_message_success(self, mock_publisher_class):
        """Test successful message publishing."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock the future result
        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            message_id = publisher.publish(
                message_data={"test": "data"}, attributes={"key": "value"}
            )

            assert message_id == "test-message-id"
            mock_publisher.publish.assert_called_once()

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publish_handles_not_found_error(self, mock_publisher_class):
        """Test publish handles topic not found errors."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock publish to raise NotFound
        mock_publisher.publish.side_effect = exceptions.NotFound("Topic not found")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            message_id = publisher.publish(message_data={"test": "data"})

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publish_handles_permission_denied_error(self, mock_publisher_class):
        """Test publish handles permission denied errors."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock publish to raise PermissionDenied
        mock_publisher.publish.side_effect = exceptions.PermissionDenied(
            "Access denied"
        )

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            message_id = publisher.publish(message_data={"test": "data"})

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publish_handles_generic_error(self, mock_publisher_class):
        """Test publish handles generic errors gracefully."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock publish to raise generic exception
        mock_publisher.publish.side_effect = Exception("Network error")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            message_id = publisher.publish(message_data={"test": "data"})

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_publish_with_default_attributes(self, mock_publisher_class):
        """Test publish works without explicit attributes."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()

            message_id = publisher.publish(message_data={"test": "data"})

            assert message_id == "test-message-id"

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_close_publisher(self, mock_publisher_class):
        """Test closing the publisher."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            publisher = GooglePubSubPublisher()
            publisher.close()

            mock_publisher.stop.assert_called_once()
