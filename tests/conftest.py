"""
Shared test configuration and fixtures.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock Pub/Sub before importing app
with patch.dict(
    os.environ,
    {
        "GCP_PROJECT_ID": "test-project",
        "SESSION_SECRET_KEY": "test-secret",
        "BASE_URL": "http://testserver",
    },
):
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
    Sets default return value to successful message ID.
    Tests that want to test failure scenarios should override this.
    """
    mock_event_publisher.reset_mock(return_value=None, side_effect=None)
    mock_event_publisher.publish.return_value = "mock-message-id-123"
    mock_event_publisher.publish.side_effect = None


@pytest.fixture
def sample_frameio_payload():
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
