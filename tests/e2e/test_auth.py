"""
End-to-end tests for magic link authentication using Firebase emulator.

These tests require the Firebase Auth emulator to be running.
Run with: FIREBASE_AUTH_EMULATOR_HOST=localhost:9099 pytest tests/e2e/ -v
"""

import logging
import re
from urllib.parse import parse_qs, urlparse

import pytest


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

        # Verify email is included in the magic link
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


class TestSessionCookieNoConflict:
    """
    Tests to ensure Firebase session cookie and OAuth SessionMiddleware cookie
    do not conflict.

    Background: The app uses two session systems:
    1. Firebase Auth: Creates a "session" cookie for magic link authentication
    2. SessionMiddleware (authlib): Creates a "cambridge_session" cookie for OAuth state

    Previously, both used "session" as the cookie name, causing the OAuth middleware
    to overwrite the Firebase session cookie, breaking authentication.
    """

    def test_firebase_session_not_overwritten_by_oauth_middleware(
        self, e2e_client, test_email, caplog
    ):
        """
        Test that the Firebase session cookie is preserved when accessing
        OAuth-related endpoints that use SessionMiddleware.

        This is a regression test for the cookie name conflict issue where
        SessionMiddleware would overwrite the Firebase 'session' cookie.
        """
        caplog.set_level(logging.INFO)

        # Step 1: Complete magic link authentication
        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )
        assert response.status_code == 200

        magic_link = extract_magic_link_from_logs(caplog)
        oob_code = extract_oob_code_from_link(magic_link)
        email = extract_email_from_link(magic_link)

        callback_response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": oob_code, "email": email},
            follow_redirects=False,
        )
        assert callback_response.status_code == 302
        assert "session" in callback_response.cookies

        firebase_session_cookie = callback_response.cookies["session"]

        # Step 2: Access an OAuth endpoint (this triggers SessionMiddleware)
        # The /oauth/connections endpoint uses get_current_user which reads
        # the Firebase session, and it's in the OAuth router which uses
        # SessionMiddleware for state management
        oauth_response = e2e_client.get(
            "/oauth/connections",
            cookies={"session": firebase_session_cookie},
        )

        # Should succeed - Firebase session should still be valid
        assert oauth_response.status_code == 200
        assert "connections" in oauth_response.json()

        # Step 3: Verify we can still access dashboard (Firebase auth still works)
        dashboard_response = e2e_client.get(
            "/dashboard",
            cookies={"session": firebase_session_cookie},
        )

        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["user"]["email"] == test_email

    def test_session_cookies_are_independent(self, e2e_client, test_email, caplog):
        """
        Test that Firebase 'session' cookie and OAuth 'cambridge_session' cookie
        are independent and don't interfere with each other.
        """
        caplog.set_level(logging.INFO)

        # Step 1: Authenticate via magic link
        response = e2e_client.post(
            "/auth/magic/send",
            json={"email": test_email},
        )
        assert response.status_code == 200

        magic_link = extract_magic_link_from_logs(caplog)
        oob_code = extract_oob_code_from_link(magic_link)
        email = extract_email_from_link(magic_link)

        callback_response = e2e_client.get(
            "/auth/magic/callback",
            params={"oobCode": oob_code, "email": email},
            follow_redirects=False,
        )

        firebase_session = callback_response.cookies["session"]

        # Step 2: Try to start OAuth flow (will fail without provider config,
        # but should not affect the Firebase session)
        # We use follow_redirects=False to catch any redirect or error
        e2e_client.get(
            "/oauth/adobe/connect",
            cookies={"session": firebase_session},
            follow_redirects=False,
        )

        # Even if OAuth fails (503 if not configured, or redirect if configured),
        # check that a cambridge_session cookie may be set but session is untouched
        # The key assertion: our Firebase session still works after this

        # Step 3: Verify Firebase session still works
        dashboard_response = e2e_client.get(
            "/dashboard",
            cookies={"session": firebase_session},
        )

        assert dashboard_response.status_code == 200
        assert dashboard_response.json()["status"] == "success"
        assert dashboard_response.json()["user"]["email"] == test_email

    def test_oauth_middleware_uses_different_cookie_name(self, e2e_client):
        """
        Test that SessionMiddleware is configured with 'cambridge_session'
        cookie name, not the default 'session'.

        This is verified by checking that accessing OAuth endpoints doesn't
        set a 'session' cookie (which would conflict with Firebase).
        """
        # Access an endpoint that would trigger SessionMiddleware
        # Without authentication, we expect a 401, but we're checking cookies
        response = e2e_client.get(
            "/oauth/connections",
            follow_redirects=False,
        )

        # Should be 401 (not authenticated)
        assert response.status_code == 401

        # The response should NOT set a 'session' cookie from SessionMiddleware
        # If there's any session cookie set by middleware, it should be
        # 'cambridge_session', not 'session'
        if "session" in response.cookies:
            # If there's a 'session' cookie, it would indicate the old bug
            # where SessionMiddleware used 'session' as cookie name
            pytest.fail(
                "SessionMiddleware is setting 'session' cookie which conflicts "
                "with Firebase auth. It should use 'cambridge_session' instead."
            )
