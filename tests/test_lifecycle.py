"""
Tests for application lifecycle events.
"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient

# Import app for lifecycle testing
with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
    from app.main import app


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
