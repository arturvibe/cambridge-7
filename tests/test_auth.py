"""
Tests for magic link authentication endpoints.
"""

import os
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient

# Set environment variables before importing app
with patch.dict(
    os.environ,
    {
        "GCP_PROJECT_ID": "test-project",
        "FIREBASE_WEB_API_KEY": "test-api-key",
        "BASE_URL": "http://localhost:8080",
    },
):
    from app.main import app
    from app.auth.config import get_auth_config, AuthConfig
    from app.auth.dependencies import get_current_user
    from app.api.magic import (
        get_magic_link_service,
        get_token_exchange_service,
        get_session_cookie_service,
    )


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_auth_config():
    """Mock auth config that passes validation."""
    config = MagicMock(spec=AuthConfig)
    config.firebase_web_api_key = "test-api-key"
    config.base_url = "http://localhost:8080"
    config.callback_url = "http://localhost:8080/auth/magic/callback"
    config.session_cookie_name = "session"
    config.session_cookie_max_age = 1209600
    config.validate.return_value = None
    return config


@pytest.fixture
def client_with_mock_config(mock_auth_config):
    """Test client with mocked auth config."""
    app.dependency_overrides[get_auth_config] = lambda: mock_auth_config
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_auth_config, None)


@pytest.fixture
def client():
    """Basic test client."""
    return TestClient(app)


# ============================================================================
# POST /auth/magic/send Tests
# ============================================================================


class TestMagicLinkSendEndpoint:
    """Tests for the POST /auth/magic/send endpoint."""

    def test_send_generates_magic_link(self, mock_auth_config):
        """Test successful magic link generation."""
        # Setup service mock
        mock_service = MagicMock()
        mock_service.generate_magic_link.return_value = (
            "https://example.firebaseapp.com/__/auth/action?oobCode=test123"
        )

        app.dependency_overrides[get_auth_config] = lambda: mock_auth_config
        app.dependency_overrides[get_magic_link_service] = lambda: mock_service
        client = TestClient(app)

        try:
            response = client.post(
                "/auth/magic/send",
                json={"email": "test@example.com"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Magic link generated" in data["message"]
            mock_service.generate_magic_link.assert_called_once_with("test@example.com")
        finally:
            app.dependency_overrides.pop(get_auth_config, None)
            app.dependency_overrides.pop(get_magic_link_service, None)

    def test_send_requires_email(self, client_with_mock_config):
        """Test that send endpoint requires email field."""
        response = client_with_mock_config.post("/auth/magic/send", json={})

        assert response.status_code == 422  # Validation error

    def test_send_validates_email_format(self, client_with_mock_config):
        """Test that send endpoint validates email format."""
        response = client_with_mock_config.post(
            "/auth/magic/send", json={"email": "not-an-email"}
        )

        assert response.status_code == 422  # Validation error

    def test_send_handles_firebase_error(self, mock_auth_config):
        """Test error handling when Firebase fails."""
        from app.auth.services import AuthenticationError

        mock_service = MagicMock()
        mock_service.generate_magic_link.side_effect = AuthenticationError(
            "Firebase error"
        )

        app.dependency_overrides[get_auth_config] = lambda: mock_auth_config
        app.dependency_overrides[get_magic_link_service] = lambda: mock_service
        client = TestClient(app)

        try:
            response = client.post(
                "/auth/magic/send", json={"email": "test@example.com"}
            )

            assert response.status_code == 500
            assert "Firebase error" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_config, None)
            app.dependency_overrides.pop(get_magic_link_service, None)

    def test_send_requires_firebase_api_key(self):
        """Test that send fails without Firebase API key."""
        # Create config with empty API key
        invalid_config = MagicMock(spec=AuthConfig)
        invalid_config.firebase_web_api_key = ""
        invalid_config.base_url = "http://localhost:8080"
        invalid_config.validate.side_effect = ValueError(
            "FIREBASE_WEB_API_KEY environment variable is required"
        )

        app.dependency_overrides[get_auth_config] = lambda: invalid_config
        client = TestClient(app)

        try:
            response = client.post(
                "/auth/magic/send", json={"email": "test@example.com"}
            )
            assert response.status_code == 500
            assert "FIREBASE_WEB_API_KEY" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_config, None)


# ============================================================================
# GET /auth/magic/callback Tests
# ============================================================================


class TestMagicLinkCallbackEndpoint:
    """Tests for the GET /auth/magic/callback endpoint."""

    def test_callback_sets_session_cookie(self, mock_auth_config):
        """Test successful callback sets session cookie and redirects."""
        # Setup mocks
        mock_token_service = MagicMock()
        mock_token_service.exchange_oob_code_for_id_token = AsyncMock(
            return_value="mock-id-token"
        )

        mock_session_service = MagicMock()
        mock_session_service.create_session_cookie.return_value = "mock-session-cookie"

        app.dependency_overrides[get_auth_config] = lambda: mock_auth_config
        app.dependency_overrides[get_token_exchange_service] = (
            lambda: mock_token_service
        )
        app.dependency_overrides[get_session_cookie_service] = (
            lambda: mock_session_service
        )
        client = TestClient(app)

        try:
            response = client.get(
                "/auth/magic/callback",
                params={"oobCode": "test-oob-code", "email": "test@example.com"},
                follow_redirects=False,
            )

            # Should redirect to dashboard
            assert response.status_code == 302
            assert response.headers["location"] == "/dashboard"

            # Should set session cookie
            assert "session" in response.cookies
        finally:
            app.dependency_overrides.pop(get_auth_config, None)
            app.dependency_overrides.pop(get_token_exchange_service, None)
            app.dependency_overrides.pop(get_session_cookie_service, None)

    def test_callback_requires_oob_code(self, client_with_mock_config):
        """Test that callback requires oobCode parameter."""
        response = client_with_mock_config.get(
            "/auth/magic/callback",
            params={"email": "test@example.com"},
        )

        assert response.status_code == 422  # Missing required query param

    def test_callback_requires_email(self, client_with_mock_config):
        """Test that callback requires email parameter."""
        response = client_with_mock_config.get(
            "/auth/magic/callback",
            params={"oobCode": "test-oob-code"},
        )

        assert response.status_code == 400
        assert "Email parameter is required" in response.json()["detail"]

    def test_callback_handles_invalid_oob_code(self, mock_auth_config):
        """Test callback handles invalid oobCode."""
        from app.auth.services import AuthenticationError

        mock_token_service = MagicMock()
        mock_token_service.exchange_oob_code_for_id_token = AsyncMock(
            side_effect=AuthenticationError("Invalid oobCode")
        )

        app.dependency_overrides[get_auth_config] = lambda: mock_auth_config
        app.dependency_overrides[get_token_exchange_service] = (
            lambda: mock_token_service
        )
        client = TestClient(app)

        try:
            response = client.get(
                "/auth/magic/callback",
                params={"oobCode": "invalid-code", "email": "test@example.com"},
            )

            assert response.status_code == 401
            assert "Invalid oobCode" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_auth_config, None)
            app.dependency_overrides.pop(get_token_exchange_service, None)


# ============================================================================
# GET /dashboard Tests
# ============================================================================


class TestDashboardEndpoint:
    """Tests for the GET /dashboard protected endpoint."""

    def test_dashboard_requires_authentication(self):
        """Test that dashboard returns 401 without session cookie."""
        from fastapi import HTTPException, status

        async def no_auth_user():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated - no session cookie",
            )

        app.dependency_overrides[get_current_user] = no_auth_user
        client = TestClient(app)

        try:
            response = client.get("/dashboard")
            assert response.status_code == 401
            assert "Not authenticated" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_dashboard_accepts_valid_session(self):
        """Test dashboard accepts valid session cookie."""

        async def mock_user():
            return {
                "uid": "test-user-id",
                "email": "test@example.com",
            }

        app.dependency_overrides[get_current_user] = mock_user
        client = TestClient(app)

        try:
            response = client.get("/dashboard")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Welcome, you are authenticated" in data["message"]
            assert data["user"]["uid"] == "test-user-id"
            assert data["user"]["email"] == "test@example.com"
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_dashboard_rejects_invalid_session(self):
        """Test dashboard rejects invalid session cookie."""
        from fastapi import HTTPException, status

        async def invalid_session():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid session cookie",
            )

        app.dependency_overrides[get_current_user] = invalid_session
        client = TestClient(app)

        try:
            response = client.get("/dashboard")
            assert response.status_code == 401
            assert "Invalid session cookie" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    def test_dashboard_rejects_expired_session(self):
        """Test dashboard rejects expired session cookie."""
        from fastapi import HTTPException, status

        async def expired_session():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Expired session cookie",
            )

        app.dependency_overrides[get_current_user] = expired_session
        client = TestClient(app)

        try:
            response = client.get("/dashboard")
            assert response.status_code == 401
            assert "Expired session cookie" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Service Unit Tests
# ============================================================================


class TestAuthConfig:
    """Tests for AuthConfig."""

    def test_config_loads_from_environment(self):
        """Test config loads values from environment."""
        with patch.dict(
            os.environ,
            {
                "FIREBASE_WEB_API_KEY": "test-key-123",
                "BASE_URL": "https://example.com",
            },
        ):
            from app.auth.config import AuthConfig

            config = AuthConfig()
            assert config.firebase_web_api_key == "test-key-123"
            assert config.base_url == "https://example.com"
            assert config.callback_url == "https://example.com/auth/magic/callback"

    def test_config_validation_requires_api_key(self):
        """Test config validation fails without API key."""
        from app.auth.config import AuthConfig

        config = AuthConfig()
        config.firebase_web_api_key = ""

        with pytest.raises(ValueError, match="FIREBASE_WEB_API_KEY"):
            config.validate()


class TestMagicLinkService:
    """Tests for MagicLinkService."""

    @patch("app.auth.services.get_firebase_auth")
    @patch("app.auth.services.get_auth_config")
    def test_generate_magic_link_calls_firebase(self, mock_get_config, mock_get_auth):
        """Test magic link generation calls Firebase correctly."""
        from app.auth.services import MagicLinkService

        # Setup mocks
        mock_config = MagicMock()
        mock_config.callback_url = "http://localhost:8080/auth/magic/callback"
        mock_get_config.return_value = mock_config

        mock_firebase = MagicMock()
        mock_firebase.generate_sign_in_with_email_link.return_value = (
            "https://example.firebaseapp.com/__/auth/action"
        )
        mock_get_auth.return_value = mock_firebase

        service = MagicLinkService()
        link = service.generate_magic_link("test@example.com")

        assert link == "https://example.firebaseapp.com/__/auth/action"
        mock_firebase.generate_sign_in_with_email_link.assert_called_once()


class TestSessionCookieService:
    """Tests for SessionCookieService."""

    @patch("app.auth.services.get_firebase_auth")
    @patch("app.auth.services.get_auth_config")
    def test_create_session_cookie(self, mock_get_config, mock_get_auth):
        """Test session cookie creation."""
        from app.auth.services import SessionCookieService

        mock_config = MagicMock()
        mock_config.session_cookie_max_age = 1209600
        mock_get_config.return_value = mock_config

        mock_firebase = MagicMock()
        mock_firebase.create_session_cookie.return_value = "session-cookie-value"
        mock_get_auth.return_value = mock_firebase

        service = SessionCookieService()
        cookie = service.create_session_cookie("id-token")

        assert cookie == "session-cookie-value"
        mock_firebase.create_session_cookie.assert_called_once_with(
            id_token="id-token",
            expires_in=1209600,
        )

    @patch("app.auth.services.get_firebase_auth")
    @patch("app.auth.services.get_auth_config")
    def test_verify_session_cookie(self, mock_get_config, mock_get_auth):
        """Test session cookie verification."""
        from app.auth.services import SessionCookieService

        mock_config = MagicMock()
        mock_get_config.return_value = mock_config

        mock_firebase = MagicMock()
        mock_firebase.verify_session_cookie.return_value = {
            "uid": "test-uid",
            "email": "test@example.com",
        }
        mock_get_auth.return_value = mock_firebase

        service = SessionCookieService()
        claims = service.verify_session_cookie("session-cookie")

        assert claims["uid"] == "test-uid"
        assert claims["email"] == "test@example.com"
        mock_firebase.verify_session_cookie.assert_called_once_with(
            session_cookie="session-cookie",
            check_revoked=True,
        )


class TestTokenExchangeService:
    """Tests for TokenExchangeService."""

    @pytest.mark.asyncio
    @patch("app.auth.services.get_auth_config")
    async def test_exchange_oob_code_success(self, mock_get_config):
        """Test successful oobCode exchange for ID token."""
        from app.auth.services import TokenExchangeService

        mock_config = MagicMock()
        mock_config.firebase_web_api_key = "test-api-key"
        mock_get_config.return_value = mock_config

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"idToken": "mock-id-token"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            service = TokenExchangeService()
            token = await service.exchange_oob_code_for_id_token(
                oob_code="test-oob-code",
                email="test@example.com",
            )

            assert token == "mock-id-token"

    @pytest.mark.asyncio
    @patch("app.auth.services.get_auth_config")
    async def test_exchange_oob_code_firebase_error(self, mock_get_config):
        """Test oobCode exchange handles Firebase errors."""
        from app.auth.services import TokenExchangeService, AuthenticationError

        mock_config = MagicMock()
        mock_config.firebase_web_api_key = "test-api-key"
        mock_get_config.return_value = mock_config

        # Create mock error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "INVALID_OOB_CODE"}}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            service = TokenExchangeService()

            with pytest.raises(AuthenticationError, match="INVALID_OOB_CODE"):
                await service.exchange_oob_code_for_id_token(
                    oob_code="invalid-code",
                    email="test@example.com",
                )
