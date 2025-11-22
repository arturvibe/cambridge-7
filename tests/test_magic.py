import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.firebase_auth import FirebaseAuthAdapter
from app.main import app, get_auth_adapter

client = TestClient(app)


@pytest.fixture
def mock_auth_adapter():
    """Fixture to mock FirebaseAuthAdapter."""
    mock_adapter = MagicMock(spec=FirebaseAuthAdapter)

    # Setup async mock returns
    mock_adapter.generate_email_link = AsyncMock(
        return_value=(
            "https://project.firebaseapp.com/__/auth/action"
            "?mode=signIn&oobCode=TEST_CODE"
        )
    )
    mock_adapter.exchange_code_for_token = AsyncMock(return_value="fake-id-token")
    mock_adapter.create_session_cookie = AsyncMock(return_value="fake-session-cookie")
    mock_adapter.verify_session_cookie = AsyncMock(
        return_value={"email": "test@example.com", "uid": "test-uid"}
    )

    # Override dependency
    app.dependency_overrides[get_auth_adapter] = lambda: mock_adapter
    yield mock_adapter
    # Cleanup
    del app.dependency_overrides[get_auth_adapter]


class TestMagicLink:
    """Tests for Magic Link Authentication."""

    def test_send_magic_link(self, mock_auth_adapter, caplog):
        """Test generating a magic link logs the correct URL."""
        email = "test@example.com"

        with caplog.at_level(logging.INFO):
            response = client.post("/auth/magic/send", json={"email": email})

        assert response.status_code == 200
        assert "Magic link generated" in response.json()["message"]

        # Verify log contains the direct link
        assert "http://testserver/auth/magic/callback" in caplog.text
        assert "oobCode=TEST_CODE" in caplog.text
        assert f"email={email}" in caplog.text

        # Verify adapter call
        mock_auth_adapter.generate_email_link.assert_called_once()
        args = mock_auth_adapter.generate_email_link.call_args
        assert args[0][0] == email
        assert "/auth/magic/callback" in args[0][1]

    def test_magic_callback(self, mock_auth_adapter):
        """Test callback exchanges code and sets cookie."""
        oob_code = "TEST_CODE"
        email = "test@example.com"

        response = client.get(
            f"/auth/magic/callback?oobCode={oob_code}&email={email}",
            allow_redirects=False,  # Don't follow redirect to check cookie
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/dashboard"

        # Verify cookie
        assert "session=fake-session-cookie" in response.headers["set-cookie"]

        # Verify adapter calls
        mock_auth_adapter.exchange_code_for_token.assert_called_with(email, oob_code)
        mock_auth_adapter.create_session_cookie.assert_called_with("fake-id-token")

    def test_dashboard_authenticated(self, mock_auth_adapter):
        """Test dashboard access with valid cookie."""
        client.cookies.set("session", "fake-session-cookie")

        response = client.get("/dashboard")

        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

        mock_auth_adapter.verify_session_cookie.assert_called_with(
            "fake-session-cookie"
        )

    def test_dashboard_unauthenticated(self):
        """Test dashboard access without cookie."""
        client.cookies.clear()

        response = client.get("/dashboard")

        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    def test_dashboard_invalid_cookie(self, mock_auth_adapter):
        """Test dashboard access with invalid cookie."""
        mock_auth_adapter.verify_session_cookie.side_effect = Exception(
            "Invalid cookie"
        )
        client.cookies.set("session", "invalid-cookie")

        response = client.get("/dashboard")

        assert response.status_code == 401
        assert "Invalid session" in response.json()["detail"]

    def test_send_magic_link_failure(self, mock_auth_adapter):
        """Test error handling when link generation fails."""
        mock_auth_adapter.generate_email_link.side_effect = Exception("Firebase error")

        response = client.post("/auth/magic/send", json={"email": "test@example.com"})

        assert response.status_code == 500
        assert "Firebase error" in response.json()["detail"]

    def test_callback_failure(self, mock_auth_adapter):
        """Test error handling in callback."""
        mock_auth_adapter.exchange_code_for_token.side_effect = ValueError(
            "Invalid code"
        )

        response = client.get(
            "/auth/magic/callback?oobCode=BAD_CODE&email=test@example.com"
        )

        assert response.status_code == 400
        assert "Authentication failed" in response.json()["detail"]
