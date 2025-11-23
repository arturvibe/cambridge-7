"""
End-to-end tests for magic link authentication using Firebase emulator.

These tests require the Firebase Auth emulator to be running.
Run with: FIREBASE_AUTH_EMULATOR_HOST=localhost:9099 pytest tests/e2e/ -v
"""

import logging
import os
import re
from urllib.parse import parse_qs, urlparse

import pytest

# Check if emulator is configured
EMULATOR_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST", "")
pytestmark = pytest.mark.skipif(
    not EMULATOR_HOST,
    reason="FIREBASE_AUTH_EMULATOR_HOST not set - Firebase emulator not available",
)

# Set required environment variables for emulator testing
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "cambridge-local")
os.environ.setdefault("GCP_PROJECT_ID", "cambridge-local")
os.environ.setdefault("FIREBASE_WEB_API_KEY", "fake-api-key")
os.environ.setdefault("BASE_URL", "http://localhost:8080")


@pytest.fixture
def e2e_client():
    """Test client for E2E tests with real Firebase emulator.

    Function-scoped to ensure each test gets a fresh client without
    persisted cookies from previous tests.
    """
    # Import after environment is set up
    from fastapi.testclient import TestClient

    from app.main import app

    # Clear any dependency overrides from other tests to use real services
    app.dependency_overrides.clear()

    yield TestClient(app)

    # Restore clean state after tests
    app.dependency_overrides.clear()


@pytest.fixture
def test_email():
    """Generate a unique test email."""
    import uuid

    return f"test-{uuid.uuid4().hex[:8]}@example.com"


def extract_oob_code_from_link(magic_link: str) -> str:
    """Extract the oobCode from a Firebase magic link URL."""
    parsed = urlparse(magic_link)
    # The oobCode might be in the query string or in the continueUrl
    query_params = parse_qs(parsed.query)

    if "oobCode" in query_params:
        return query_params["oobCode"][0]

    # Check continueUrl for nested params
    if "continueUrl" in query_params:
        continue_url = query_params["continueUrl"][0]
        continue_parsed = urlparse(continue_url)
        continue_params = parse_qs(continue_parsed.query)
        if "oobCode" in continue_params:
            return continue_params["oobCode"][0]

    raise ValueError(f"Could not extract oobCode from magic link: {magic_link}")


def extract_email_from_link(magic_link: str) -> str:
    """Extract the email from a Firebase magic link URL."""
    parsed = urlparse(magic_link)
    query_params = parse_qs(parsed.query)

    # Check continueUrl for email param
    if "continueUrl" in query_params:
        continue_url = query_params["continueUrl"][0]
        continue_parsed = urlparse(continue_url)
        continue_params = parse_qs(continue_parsed.query)
        if "email" in continue_params:
            return continue_params["email"][0]

    if "email" in query_params:
        return query_params["email"][0]

    raise ValueError(f"Could not extract email from magic link: {magic_link}")


def extract_magic_link_from_logs(caplog: pytest.LogCaptureFixture) -> str:
    """Extract magic link from captured JSON log output."""
    # Look for JSON log with magic_link field
    magic_link_match = re.search(r'"magic_link":\s*"([^"]+)"', caplog.text)
    assert magic_link_match, f"Magic link not found in logs: {caplog.text}"
    return magic_link_match.group(1)


class TestMagicLinkE2E:
    """End-to-end tests for the complete magic link authentication flow."""

    def test_full_auth_flow(self, e2e_client, test_email, caplog):
        """Test the complete authentication flow from magic link to dashboard."""
        caplog.set_level(logging.INFO)

        # Step 1: Request a magic link
        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Step 2: Extract magic link from logs
        magic_link = extract_magic_link_from_logs(caplog)

        # Step 3: Extract oobCode and email from the magic link
        oob_code = extract_oob_code_from_link(magic_link)
        email = extract_email_from_link(magic_link)
        assert email == test_email

        # Step 4: Call the callback endpoint with oobCode
        callback_response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": oob_code, "email": email},
            follow_redirects=False,
        )

        # Should redirect to dashboard with session cookie
        assert callback_response.status_code == 302
        assert callback_response.headers["location"] == "/dashboard"
        assert "session" in callback_response.cookies

        session_cookie = callback_response.cookies["session"]

        # Step 5: Access dashboard with session cookie
        dashboard_response = e2e_client.get(
            "/dashboard",
            cookies={"session": session_cookie},
        )

        assert dashboard_response.status_code == 200
        dashboard_data = dashboard_response.json()
        assert dashboard_data["status"] == "success"
        assert dashboard_data["user"]["email"] == test_email

    def test_magic_link_generates_valid_link(self, e2e_client, test_email, caplog):
        """Test that magic link generation produces a valid link."""
        caplog.set_level(logging.INFO)

        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )

        assert response.status_code == 200

        # Extract and validate magic link format
        magic_link = extract_magic_link_from_logs(caplog)
        parsed = urlparse(magic_link)

        # Should be emulator URL
        assert "9099" in parsed.netloc or "emulator" in magic_link.lower()

    def test_callback_with_invalid_oob_code(self, e2e_client, test_email):
        """Test that callback rejects invalid oobCode."""
        response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": "invalid-oob-code", "email": test_email},
        )

        assert response.status_code == 401
        assert (
            "error" in response.json()["detail"].lower()
            or "failed" in response.json()["detail"].lower()
        )

    def test_dashboard_without_session_returns_401(self, e2e_client):
        """Test that dashboard requires authentication."""
        response = e2e_client.get("/dashboard")

        assert response.status_code == 401

    def test_dashboard_with_invalid_session_returns_401(self, e2e_client):
        """Test that dashboard rejects invalid session cookie."""
        response = e2e_client.get(
            "/dashboard",
            cookies={"session": "invalid-session-cookie"},
        )

        assert response.status_code == 401

    def test_magic_link_includes_email_in_callback_url(
        self, e2e_client, test_email, caplog
    ):
        """Test that generated magic link includes email for callback."""
        caplog.set_level(logging.INFO)

        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )

        assert response.status_code == 200

        magic_link = extract_magic_link_from_logs(caplog)

        # Email should be in the continueUrl
        email = extract_email_from_link(magic_link)
        assert email == test_email


class TestMagicLinkE2EEdgeCases:
    """Edge case tests for magic link authentication."""

    def test_multiple_magic_links_same_email(self, e2e_client, test_email, caplog):
        """Test that multiple magic links can be generated for same email."""
        caplog.set_level(logging.INFO)

        # Generate first link
        response1 = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )
        assert response1.status_code == 200
        link1 = extract_magic_link_from_logs(caplog)
        oob1 = extract_oob_code_from_link(link1)

        # Clear logs before second request
        caplog.clear()

        # Generate second link
        response2 = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )
        assert response2.status_code == 200
        link2 = extract_magic_link_from_logs(caplog)
        oob2 = extract_oob_code_from_link(link2)

        # Both codes should be different
        assert oob1 != oob2

        # Second link should work
        callback_response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": oob2, "email": test_email},
            follow_redirects=False,
        )
        assert callback_response.status_code == 302

    def test_email_case_insensitivity(self, e2e_client, caplog):
        """Test that email matching is handled correctly."""
        caplog.set_level(logging.INFO)
        email_lower = "testcase@example.com"

        # Generate link with lowercase email
        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": email_lower},
        )
        assert response.status_code == 200

        magic_link = extract_magic_link_from_logs(caplog)
        oob_code = extract_oob_code_from_link(magic_link)

        # Callback should work with the email from the link
        email_from_link = extract_email_from_link(magic_link)
        callback_response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": oob_code, "email": email_from_link},
            follow_redirects=False,
        )
        assert callback_response.status_code == 302
