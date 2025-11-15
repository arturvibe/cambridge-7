"""
Unit tests for the Cambridge FastAPI webhook application.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
                "name": "sample_video.mp4"
            },
            "account": {
                "id": "account-123"
            },
            "workspace": {
                "id": "workspace-456"
            },
            "project": {
                "id": "project-789"
            },
            "user": {
                "id": "user-xyz"
            }
        }

    def test_webhook_accepts_valid_payload(self, sample_frameio_payload):
        """Test webhook accepts valid Frame.io payload."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json=sample_frameio_payload,
            headers={"Content-Type": "application/json"}
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
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200

        # Check that important information was logged
        log_text = caplog.text
        assert "FRAME.IO WEBHOOK RECEIVED" in log_text
        assert "Event Type: resource.asset_created" in log_text
        assert "Resource Type: asset" in log_text
        assert "Resource ID: abc-123-def-456" in log_text

    def test_webhook_handles_minimal_payload(self):
        """Test webhook handles minimal payload with missing optional fields."""
        minimal_payload = {
            "type": "unknown_event",
            "resource": {}
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=minimal_payload,
            headers={"Content-Type": "application/json"}
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
                data="invalid json{{{",
                headers={"Content-Type": "application/json"}
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
                headers={"Content-Type": "application/json"}
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
            headers={"Content-Type": "application/json"}
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
                "metadata": {
                    "large_field": "x" * 10000  # 10KB of data
                }
            }
        }

        response = client.post(
            "/api/v1/frameio/webhook",
            json=large_payload,
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200

    def test_webhook_handles_empty_payload(self):
        """Test webhook handles empty payload."""
        response = client.post(
            "/api/v1/frameio/webhook",
            json={},
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"
        assert data["event_type"] == "unknown"
