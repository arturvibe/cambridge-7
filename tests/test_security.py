"""
Tests for endpoint security and edge cases.
"""

from tests.conftest import client


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
        """Test webhook returns 422 for empty payload (validation)."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json={},
            headers={"Content-Type": "application/json"},
        )

        # Custom exception handler returns 422 for missing fields
        assert response.status_code == 422
        data = response.json()
        assert "details" in data  # Custom exception handler format
        assert data["status"] == "error"
        assert "Invalid payload schema" in data["message"]
