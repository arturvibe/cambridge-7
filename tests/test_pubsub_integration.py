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
        """Test webhook publishes message to Pub/Sub."""
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

        # Verify publish was called with correct data
        mock_event_publisher.publish.assert_called_once()
        call_args = mock_event_publisher.publish.call_args

        # Check message data (should be the domain model dict)
        message_data = call_args.kwargs["message_data"]
        assert message_data["type"] == "file.created"

        # Check attributes
        attributes = call_args.kwargs["attributes"]
        assert attributes["event_type"] == "file.created"
        assert attributes["resource_type"] == "file"
        assert attributes["resource_id"] == "file-123"

    def test_webhook_returns_500_if_pubsub_fails(self, sample_payload):
        """Test webhook returns 500 if Pub/Sub publishing fails so Frame.io can retry."""
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
        assert "Failed to publish event to Pub/Sub" in data["message"]

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
        assert "Failed to publish event to Pub/Sub" in data["message"]

    def test_webhook_pubsub_attributes_with_complete_payload(self):
        """Test Pub/Sub attributes are set correctly for complete payload."""
        # Configure mock's return value
        mock_event_publisher.publish.return_value = "msg-id-456"

        complete_payload = {
            "type": "unknown_event",
            "resource": {"type": "asset", "id": "asset-123"},
            "account": {"id": "account-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=complete_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

        # Verify attributes are set correctly
        call_args = mock_event_publisher.publish.call_args
        attributes = call_args.kwargs["attributes"]
        assert attributes["event_type"] == "unknown_event"
        assert attributes["resource_type"] == "asset"
        assert attributes["resource_id"] == "asset-123"
