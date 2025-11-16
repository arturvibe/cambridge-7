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
    from app.main import app, get_event_publisher

# Create a single mock publisher for all tests
mock_event_publisher = MagicMock()

# Use FastAPI's dependency_overrides to replace the real publisher with our mock
app.dependency_overrides[get_event_publisher] = lambda: mock_event_publisher

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_mock_event_publisher():
    """
    Reset the mock event publisher before each test.

    This fixture runs automatically for every test (autouse=True).
    Sets default return value to None to avoid MagicMock serialization issues.
    """
    mock_event_publisher.reset_mock(return_value=None, side_effect=None)
    mock_event_publisher.publish.return_value = None


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
        assert "message_id" in data

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
        """Test webhook handles payload with all required fields."""
        minimal_payload = {
            "type": "unknown_event",
            "resource": {"type": "asset", "id": "resource-123"},
            "account": {"id": "account-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=minimal_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data

    def test_webhook_handles_invalid_json(self, caplog):
        """Test webhook handles invalid JSON gracefully."""
        with caplog.at_level("ERROR"):
            response = client.post(
                "/api/v1/frameio/webhook",
                content=b"invalid json{{{",
                headers={"Content-Type": "application/json"},
            )

        # Invalid JSON returns 500 error
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"

        # Should log error about JSON parsing
        assert "Failed to parse JSON payload" in caplog.text

    def test_webhook_extracts_all_frameio_fields(self, sample_frameio_payload):
        """Test webhook correctly extracts all Frame.io V4 fields."""
        with patch("app.api.frameio.logger") as mock_logger:
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

        # Verify response structure contains only message_id
        assert "message_id" in data
        assert len(data) == 1


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
            "account": {"id": "account-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=large_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200

    def test_webhook_handles_empty_payload(self):
        """Test webhook rejects empty payload (missing required fields)."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json={},
            headers={"Content-Type": "application/json"},
        )

        # Empty payload returns 500 error (missing required fields)
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"


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

    def test_webhook_continues_if_pubsub_fails(self, sample_payload):
        """Test webhook still succeeds if Pub/Sub publishing fails."""
        # Configure mock to raise an exception
        mock_event_publisher.publish.side_effect = Exception("Pub/Sub error")

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        # Webhook should still return 200 even if Pub/Sub fails
        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] is None

    def test_webhook_when_pubsub_disabled(self, sample_payload):
        """Test webhook works when Pub/Sub returns None."""
        # Configure mock to return None (disabled)
        mock_event_publisher.publish.return_value = None

        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_payload,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message_id"] is None

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


class TestApplicationLifecycle:
    """Test application lifecycle events."""

    def test_shutdown_event_closes_publisher(self):
        """Test shutdown event completes successfully and closes publisher."""
        # Ensure environment variable is set for shutdown
        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            # Shutdown event should complete without errors
            with TestClient(app) as test_client:
                # Make a request to ensure the app works
                response = test_client.post(
                    "/api/v1/frameio/webhook",
                    json={
                        "type": "test",
                        "resource": {"type": "asset", "id": "asset-123"},
                        "account": {"id": "account-123"},
                        "workspace": {"id": "workspace-123"},
                        "project": {"id": "project-123"},
                        "user": {"id": "user-123"},
                    },
                )
                assert response.status_code == 200
                # TestClient context manager will trigger shutdown on exit
