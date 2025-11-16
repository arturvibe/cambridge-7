"""
Tests for health check endpoints.
"""

from datetime import datetime

from tests.conftest import client


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
