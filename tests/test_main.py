"""
Unit tests for the Cambridge FastAPI webhook application.
"""

import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock Pub/Sub before importing app
with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
    from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Test the root endpoint returns healthy status."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cambridge"
        assert "timestamp" in data

        # Validate timestamp format
        datetime.fromisoformat(data["timestamp"])

    def test_health_endpoint(self):
        """Test the /health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestFrameIOWebhook:
    """Test Frame.io webhook endpoint."""

    @pytest.fixture
    def sample_frameio_payload(self):
        """Sample Frame.io V4 webhook payload."""
        return {
            "type": "resource.asset_created",
            "resource": {
                "type": "asset",
                "id": "abc-123-def-456",
                "name": "sample_video.mp4",
            },
            "account": {"id": "account-123"},
            "workspace": {"id": "workspace-456"},
            "project": {"id": "project-789"},
            "user": {"id": "user-xyz"},
        }

    def test_webhook_accepts_valid_payload(self, sample_frameio_payload):
        """Test webhook accepts valid Frame.io payload."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_frameio_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_type"] == "resource.asset_created"

    def test_webhook_logs_payload(self, sample_frameio_payload, caplog):
        """Test webhook logs the payload information."""
        with caplog.at_level("INFO"):
            response = client.post(
                "/api/v1/frameio/webhook",
                json=sample_frameio_payload,
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 200

        # Check that important information was logged as structured JSON
        log_text = caplog.text
        assert "FRAME.IO WEBHOOK RECEIVED" in log_text
        assert '"event_type": "resource.asset_created"' in log_text
        assert '"resource_type": "asset"' in log_text
        assert '"resource_id": "abc-123-def-456"' in log_text

    def test_webhook_handles_minimal_payload(self):
        """Test webhook handles minimal payload with missing optional fields."""
        minimal_payload = {"type": "unknown_event", "resource": {}}

        response = client.post(
            "/api/v1/frameio/webhook",
            json=minimal_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_type"] == "unknown_event"

    def test_webhook_handles_invalid_json(self, caplog):
        """Test webhook handles invalid JSON gracefully."""
        with caplog.at_level("ERROR"):
            response = client.post(
                "/api/v1/frameio/webhook",
                content=b"invalid json{{{",
                headers={"Content-Type": "application/json"},
            )

        # App handles invalid JSON gracefully and still returns 200
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_type"] == "unknown"

        # But it should log an error
        assert "Failed to parse JSON payload" in caplog.text

    def test_webhook_extracts_all_frameio_fields(self, sample_frameio_payload):
        """Test webhook correctly extracts all Frame.io V4 fields."""
        with patch("app.main.logger") as mock_logger:
            response = client.post(
                "/api/v1/frameio/webhook",
                json=sample_frameio_payload,
                headers={"Content-Type": "application/json"},
            )

            assert response.status_code == 200

            # Verify logger was called with expected information
            assert mock_logger.info.called
            log_calls = [str(call) for call in mock_logger.info.call_args_list]
            log_output = " ".join(log_calls)

            assert "resource.asset_created" in log_output
            assert "asset" in log_output
            assert "abc-123-def-456" in log_output

    def test_webhook_response_structure(self, sample_frameio_payload):
        """Test webhook response has correct structure."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_frameio_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "event_type" in data
        assert "resource_type" in data
        assert "timestamp" in data

        # Verify values
        assert data["status"] == "received"
        assert data["event_type"] == "resource.asset_created"
        assert data["resource_type"] == "asset"

        # Validate timestamp format
        datetime.fromisoformat(data["timestamp"])


class TestEndpointSecurity:
    """Test endpoint security and edge cases."""

    def test_webhook_accepts_post_only(self):
        """Test webhook endpoint only accepts POST requests."""
        response_get = client.get("/api/v1/frameio/webhook")
        assert response_get.status_code == 405  # Method Not Allowed

    def test_nonexistent_endpoint_returns_404(self):
        """Test accessing non-existent endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_webhook_handles_large_payload(self):
        """Test webhook can handle large payloads."""
        large_payload = {
            "type": "resource.asset_created",
            "resource": {
                "type": "asset",
                "id": "large-asset",
                "metadata": {"large_field": "x" * 10000},  # 10KB of data
            },
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=large_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

    def test_webhook_handles_empty_payload(self):
        """Test webhook handles empty payload."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json={},
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_type"] == "unknown"


class TestPubSubIntegration:
    """Test Pub/Sub integration in webhook endpoint."""

    @pytest.fixture
    def sample_payload(self):
        """Sample webhook payload."""
        return {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
        }

    @patch("app.main.pubsub_client")
    def test_webhook_publishes_to_pubsub(self, mock_pubsub_client, sample_payload):
        """Test webhook publishes message to Pub/Sub."""
        # Mock publish to return a message ID
        mock_pubsub_client.publish.return_value = "msg-id-123"

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response includes message ID
        assert data["status"] == "received"
        assert data["pubsub_message_id"] == "msg-id-123"

        # Verify publish was called with correct data
        mock_pubsub_client.publish.assert_called_once()
        call_args = mock_pubsub_client.publish.call_args

        # Check message data
        assert call_args.kwargs["message_data"] == sample_payload

        # Check attributes
        attributes = call_args.kwargs["attributes"]
        assert attributes["event_type"] == "file.created"
        assert attributes["resource_type"] == "file"
        assert attributes["resource_id"] == "file-123"

    @patch("app.main.pubsub_client")
    def test_webhook_continues_if_pubsub_fails(self, mock_pubsub_client, sample_payload):
        """Test webhook still succeeds if Pub/Sub publishing fails."""
        # Mock publish to raise an exception
        mock_pubsub_client.publish.side_effect = Exception("Pub/Sub error")

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        # Webhook should still return 200 even if Pub/Sub fails
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "pubsub_message_id" not in data

    @patch("app.main.pubsub_client")
    def test_webhook_when_pubsub_disabled(self, mock_pubsub_client, sample_payload):
        """Test webhook works when Pub/Sub is disabled."""
        # Mock publish to return None (disabled)
        mock_pubsub_client.publish.return_value = None

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert "pubsub_message_id" not in data

    @patch("app.main.pubsub_client")
    def test_webhook_pubsub_attributes_with_minimal_payload(self, mock_pubsub_client):
        """Test Pub/Sub attributes are set correctly for minimal payload."""
        mock_pubsub_client.publish.return_value = "msg-id-456"

        minimal_payload = {"type": "unknown_event", "resource": {}}

        response = client.post(
            "/api/v1/frameio/webhook",
            json=minimal_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

        # Verify attributes use defaults for missing fields
        call_args = mock_pubsub_client.publish.call_args
        attributes = call_args.kwargs["attributes"]
        assert attributes["event_type"] == "unknown_event"
        assert attributes["resource_type"] == "unknown"
        assert attributes["resource_id"] == "unknown"


class TestApplicationLifecycle:
    """Test application lifecycle events."""

    @patch("app.main.pubsub_client")
    def test_shutdown_event_closes_pubsub_client(self, mock_pubsub_client):
        """Test shutdown event properly closes Pub/Sub client."""
        with TestClient(app) as test_client:
            # Client context manager triggers shutdown
            pass

        # Verify close was called
        mock_pubsub_client.close.assert_called()
