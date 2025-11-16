"""
Tests for Frame.io webhook endpoint.
"""

from tests.conftest import client


class TestFrameIOWebhook:
    """Test Frame.io webhook endpoint."""

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

    def test_webhook_handles_invalid_json(self):
        """Test webhook returns 422 for invalid JSON (custom exception handler)."""
        response = client.post(
            "/api/v1/frameio/webhook",
            content=b"invalid json{{{",
            headers={"Content-Type": "application/json"},
        )

        # Custom exception handler returns 422 Unprocessable Entity for invalid JSON
        assert response.status_code == 422
        data = response.json()
        assert "details" in data  # Custom exception handler format
        assert data["status"] == "error"
        assert "Invalid payload schema" in data["message"]

    def test_webhook_extracts_all_frameio_fields(self, sample_frameio_payload, caplog):
        """Test webhook extracts all Frame.io V4 fields (logged)."""
        with caplog.at_level("INFO"):
            response = client.post(
                "/api/v1/frameio/webhook",
                json=sample_frameio_payload,
                headers={"Content-Type": "application/json"},
            )

        assert response.status_code == 200

        # Verify fields were logged in structured JSON
        log_text = caplog.text
        assert "resource.asset_created" in log_text
        assert "asset" in log_text
        assert "abc-123-def-456" in log_text

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
