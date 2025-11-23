"""
Tests for security and edge cases.
"""

from tests.conftest import client


class TestEndpointSecurity:
    """Test security and edge cases for endpoints."""

    def test_webhook_accepts_post_only(self):
        """Test that the webhook endpoint only accepts POST requests."""
        response_get = client.get("/api/v1/frameio/webhook")
        assert response_get.status_code == 405

    def test_nonexistent_endpoint_returns_404(self):
        """Test that a nonexistent endpoint returns 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_webhook_handles_large_payload(self):
        """Test that the webhook endpoint handles a large payload."""
        large_payload = {
            "type": "file.created",
            "resource": {"type": "file", "id": "file-123"},
            "account": {"id": "acc-123"},
            "workspace": {"id": "workspace-123"},
            "project": {"id": "project-123"},
            "user": {"id": "user-123"},
            "large_data": "a" * 10000,
        }
        response = client.post(
            "/api/v1/frameio/webhook",
            json=large_payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200

    def test_webhook_handles_empty_payload(self):
        """Test that the webhook endpoint handles an empty payload."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json={},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422
