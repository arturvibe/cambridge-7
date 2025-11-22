"""
Unit tests for the GooglePubSubPublisher infrastructure adapter.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions

from app.core.domain import FrameIOEvent
from app.infrastructure.pubsub_publisher import GooglePubSubPublisher


# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_event():
    """Create a sample FrameIOEvent for testing."""
    return FrameIOEvent(
        **{
            "type": "file.created",
            "resource": {"type": "file", "id": "test-file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "ws-123"},
            "project": {"id": "proj-123"},
            "user": {"id": "user-123"},
        }
    )


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
                "PUBSUB_TOPIC_NAME": "test-topic",
                "PUBSUB_EMULATOR_HOST": "localhost:8085",
            },
        ):
            publisher = GooglePubSubPublisher()

            assert publisher.emulator_host == "localhost:8085"

    def test_publisher_missing_topic_name_raises_error(self):
        """Test publisher raises error when topic name is missing."""
        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}, clear=True):
            with pytest.raises(ValueError, match="PUBSUB_TOPIC_NAME must be set"):
                GooglePubSubPublisher()


class TestGooglePubSubPublish:
    """Test publishing messages to Pub/Sub."""

    @patch("app.infrastructure.pubsub_publisher.asyncio.to_thread")
    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    async def test_publish_message_success(
        self, mock_publisher_class, mock_to_thread, sample_event
    ):
        """Test successful message publishing with domain event."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock the future
        mock_future = MagicMock()
        mock_publisher.publish.return_value = mock_future

        # Mock asyncio.to_thread to return the message ID
        mock_to_thread.return_value = "test-message-id"

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_TOPIC_NAME": "test-topic"},
        ):
            publisher = GooglePubSubPublisher()

            message_id = await publisher.publish(sample_event)

            assert message_id == "test-message-id"
            mock_publisher.publish.assert_called_once()

            # Verify attributes were extracted from domain object
            call_kwargs = mock_publisher.publish.call_args.kwargs
            assert call_kwargs["event_type"] == "file.created"
            assert call_kwargs["resource_type"] == "file"
            assert call_kwargs["resource_id"] == "test-file-123"

            # Verify asyncio.to_thread was called with the future's result method
            mock_to_thread.assert_called_once_with(mock_future.result, 10.0)

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    async def test_publish_handles_not_found_error(
        self, mock_publisher_class, sample_event
    ):
        """Test publish handles topic not found errors."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock publish to raise NotFound
        mock_publisher.publish.side_effect = exceptions.NotFound("Topic not found")

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_TOPIC_NAME": "test-topic"},
        ):
            publisher = GooglePubSubPublisher()

            message_id = await publisher.publish(sample_event)

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    async def test_publish_handles_permission_denied_error(
        self, mock_publisher_class, sample_event
    ):
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

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_TOPIC_NAME": "test-topic"},
        ):
            publisher = GooglePubSubPublisher()

            message_id = await publisher.publish(sample_event)

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.asyncio.to_thread")
    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    async def test_publish_handles_generic_error(
        self, mock_publisher_class, mock_to_thread, sample_event
    ):
        """Test publish handles generic errors gracefully."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        # Mock asyncio.to_thread to raise an exception
        mock_to_thread.side_effect = Exception("Network error")

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_TOPIC_NAME": "test-topic"},
        ):
            publisher = GooglePubSubPublisher()

            message_id = await publisher.publish(sample_event)

            assert message_id is None

    @patch("app.infrastructure.pubsub_publisher.pubsub_v1.PublisherClient")
    def test_close_publisher(self, mock_publisher_class):
        """Test closing the publisher."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/test-topic"
        )

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_TOPIC_NAME": "test-topic"},
        ):
            publisher = GooglePubSubPublisher()
            publisher.close()

            mock_publisher.stop.assert_called_once()
