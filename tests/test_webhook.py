"""
Tests for the Frame.io webhook endpoint.
"""
from tests.conftest import client


class TestFrameIOWebhook:
    """Test the Frame.io webhook endpoint."""

    def test_webhook_accepts_valid_payload(self):
        """Test that the webhook endpoint accepts a valid payload."""
        payload = {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }
        response = client.post(
            "/api/v1/frameio/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    def test_webhook_logs_payload(self, caplog):
        """Test that the webhook endpoint logs the payload."""
        payload = {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }
        client.post(
            "/api/v1/frameio/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert "file.created" in caplog.text
        assert "file-123" in caplog.text

    def test_webhook_handles_minimal_payload(self):
        """Test that the webhook endpoint handles a minimal payload."""
        payload = {"type": "file.created"}
        response = client.post(
            "/api/v1/frameio/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_webhook_handles_invalid_json(self):
        """Test that the webhook endpoint handles invalid JSON."""
        response = client.post(
            "/api/v1/frameio/webhook",
            content="{invalid json}",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_webhook_extracts_all_frameio_fields(self, caplog):
        """Test that the webhook endpoint extracts all Frame.io fields."""
        payload = {
            "type": "comment.created",
            "resource": {"type": "comment", "id": "comment-123"},
            "account": {"id": "acc-456"},
            "workspace": {"id": "workspace-789"},
            "project": {"id": "project-101"},
            "user": {"id": "user-112"},
        }
        client.post(
            "/api/v1/frameio/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        assert "comment.created" in caplog.text
        assert "comment-123" in caplog.text
        assert "acc-456" in caplog.text
        assert "workspace-789" in caplog.text
        assert "project-101" in caplog.text
        assert "user-112" in caplog.text

    def test_webhook_response_structure(self):
        """Test the structure of the webhook response."""
        payload = {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
        }
        response = client.post(
            "/api/v1/frameio/webhook",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        assert "message_id" in data
