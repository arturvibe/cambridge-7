"""
Unit tests for the PubSubClient class.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.pubsub_client import PubSubClient


class TestPubSubClient:
    """Test PubSubClient initialization and configuration."""

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_client_initialization_enabled(self, mock_publisher_class):
        """Test client initializes correctly when enabled."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient(topic_name="test-topic")

        assert client.enabled is True
        assert client.project_id == "test-project"
        assert client.topic_name == "test-topic"
        assert client.publisher is not None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_client_disabled_via_env_var(self, mock_publisher_class):
        """Test client is disabled when PUBSUB_ENABLED=false."""
        with patch.dict(os.environ, {"PUBSUB_ENABLED": "false", "GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        assert client.enabled is False
        assert client.publisher is None
        mock_publisher_class.assert_not_called()

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_client_disabled_missing_project_id(self, mock_publisher_class):
        """Test client is disabled when GCP_PROJECT_ID is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear environment and don't pass project_id
            client = PubSubClient()

        assert client.enabled is False
        assert client.publisher is None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_client_detects_emulator(self, mock_publisher_class):
        """Test client detects Pub/Sub emulator."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        with patch.dict(
            os.environ,
            {"GCP_PROJECT_ID": "test-project", "PUBSUB_EMULATOR_HOST": "localhost:8085"},
        ):
            client = PubSubClient()

        assert client.emulator_host == "localhost:8085"
        assert client.enabled is True

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_client_initialization_failure(self, mock_publisher_class):
        """Test client handles initialization failures gracefully."""
        mock_publisher_class.side_effect = Exception("Connection failed")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        assert client.enabled is False
        assert client.publisher is None


class TestPubSubPublish:
    """Test message publishing functionality."""

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_message_success(self, mock_publisher_class):
        """Test successful message publishing."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        # Mock the future result
        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id-123"
        mock_publisher.publish.return_value = mock_future

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_data = {"type": "test.event", "resource": {"id": "123"}}
        attributes = {"event_type": "test.event"}

        message_id = client.publish(message_data, attributes)

        assert message_id == "test-message-id-123"
        mock_publisher.publish.assert_called_once()

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_when_disabled(self, mock_publisher_class):
        """Test publish returns None when client is disabled."""
        with patch.dict(os.environ, {"PUBSUB_ENABLED": "false", "GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_data = {"type": "test.event"}
        message_id = client.publish(message_data)

        assert message_id is None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_handles_not_found_error(self, mock_publisher_class):
        """Test publish handles NotFound error gracefully."""
        from google.api_core import exceptions

        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        # Mock publish to raise NotFound
        mock_publisher.publish.side_effect = exceptions.NotFound("Topic not found")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_id = client.publish({"type": "test"})

        assert message_id is None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_handles_permission_denied_error(self, mock_publisher_class):
        """Test publish handles PermissionDenied error gracefully."""
        from google.api_core import exceptions

        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        # Mock publish to raise PermissionDenied
        mock_publisher.publish.side_effect = exceptions.PermissionDenied("Access denied")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_id = client.publish({"type": "test"})

        assert message_id is None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_handles_generic_error(self, mock_publisher_class):
        """Test publish handles generic errors gracefully."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        # Mock publish to raise generic exception
        mock_publisher.publish.side_effect = Exception("Network error")

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_id = client.publish({"type": "test"})

        assert message_id is None

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_publish_with_default_attributes(self, mock_publisher_class):
        """Test publish works without explicit attributes."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        mock_future = MagicMock()
        mock_future.result.return_value = "test-message-id"
        mock_publisher.publish.return_value = mock_future

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        message_id = client.publish({"type": "test"})

        assert message_id == "test-message-id"

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_close_client(self, mock_publisher_class):
        """Test closing the client."""
        mock_publisher = MagicMock()
        mock_publisher_class.return_value = mock_publisher
        mock_publisher.topic_path.return_value = "projects/test-project/topics/test-topic"

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            client = PubSubClient()

        client.close()

        mock_publisher.stop.assert_called_once()

    @patch("app.pubsub_client.pubsub_v1.PublisherClient")
    def test_close_when_disabled(self, mock_publisher_class):
        """Test closing client when it's disabled doesn't raise error."""
        with patch.dict(os.environ, {"PUBSUB_ENABLED": "false"}):
            client = PubSubClient()

        # Should not raise an error
        client.close()
