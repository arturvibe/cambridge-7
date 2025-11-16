"""
Tests for Pub/Sub integration in webhook endpoint.
"""

import pytest

from tests.conftest import client, mock_event_publisher


class TestPubSubIntegration:
    """Test Pub/Sub integration in webhook endpoint."""

    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }

    def test_webhook_publishes_to_pubsub(self, sample_payload):
        """Test webhook publishes domain event to Pub/Sub."""
        # Configure the mock's return value
        mock_event_publisher.publish.return_value = "msg-id-123"

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response includes message ID
        assert data["message_id"] == "msg-id-123"

        # Verify publish was called once with a FrameIOEvent domain object
        mock_event_publisher.publish.assert_called_once()

        # Get the argument (works for both positional and keyword args)
        call_args = mock_event_publisher.publish.call_args
        event = call_args[0][0] if call_args[0] else call_args.kwargs["event"]

        # Verify it's a FrameIOEvent domain object with correct data
        from app.core.domain import FrameIOEvent

        assert isinstance(event, FrameIOEvent)
        assert event.event_type == "file.created"
        assert event.resource_type == "file"
        assert event.resource_id == "file-123"

    def test_webhook_returns_500_if_pubsub_fails(self, sample_payload):
        """Test webhook returns 500 if Pub/Sub fails (Frame.io retries)."""
        # Configure mock to raise an exception
        mock_event_publisher.publish.side_effect = Exception("Pub/Sub error")

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        # Webhook should return 500 so Frame.io retries (event won't be lost)
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "please retry" in data["message"]

    def test_webhook_returns_500_when_pubsub_returns_none(self, sample_payload):
        """Test webhook returns 500 when Pub/Sub returns None so Frame.io can retry."""
        # Configure mock to return None (publishing failed)
        mock_event_publisher.publish.return_value = None

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        # Webhook should return 500 so Frame.io retries (event won't be lost)
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "please retry" in data["message"]
