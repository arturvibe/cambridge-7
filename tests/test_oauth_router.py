"""
Tests for OAuth router endpoints.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Set environment variables before importing app
with patch.dict(
    os.environ,
    {
        "GCP_PROJECT_ID": "test-project",
        "FIREBASE_WEB_API_KEY": "test-api-key",
        "BASE_URL": "http://localhost:8080",
        "GOOGLE_CLIENT_ID": "test-google-id",
        "GOOGLE_CLIENT_SECRET": "test-google-secret",
    },
):
    from app.main import app
    from app.auth.dependencies import get_current_user
    from app.oauth.dependencies import get_repository
    from app.oauth.config import get_oauth_config, OAuthConfig
    from app.users.repository import InMemoryUserRepository


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return {
        "uid": "test-user-123",
        "email": "test@example.com",
    }


@pytest.fixture
def mock_oauth_config():
    """Mock OAuth config."""
    config = MagicMock(spec=OAuthConfig)
    config.base_url = "http://localhost:8080"
    config.google_client_id = "test-google-id"
    config.google_client_secret = "test-google-secret"
    config.is_provider_configured.return_value = True
    config.get_callback_url.return_value = "http://localhost:8080/oauth/google/callback"
    return config


@pytest.fixture
def mock_repository():
    """Mock user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def authenticated_client(mock_user, mock_oauth_config, mock_repository):
    """Test client with mocked authentication."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config
    app.dependency_overrides[get_repository] = lambda: mock_repository

    client = TestClient(app)
    yield client

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_oauth_config, None)
    app.dependency_overrides.pop(get_repository, None)


@pytest.fixture
def unauthenticated_client(mock_oauth_config):
    """Test client without authentication but with OAuth config mocked."""
    # Remove auth override but keep OAuth config so provider validation passes
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config

    client = TestClient(app)
    yield client

    app.dependency_overrides.pop(get_oauth_config, None)


# ============================================================================
# GET /oauth/{provider}/connect Tests
# ============================================================================


class TestOAuthConnectEndpoint:
    """Tests for the GET /oauth/{provider}/connect endpoint."""

    def test_connect_requires_authentication(self, unauthenticated_client):
        """Test connect endpoint requires authentication."""
        response = unauthenticated_client.get(
            "/oauth/google/connect",
            follow_redirects=False,
        )

        assert response.status_code == 401

    def test_connect_unknown_provider_returns_404(self, mock_user, mock_oauth_config):
        """Test connect with unknown provider returns 404."""
        mock_oauth_config.is_provider_configured.return_value = False

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config

        client = TestClient(app)

        try:
            response = client.get(
                "/oauth/unknown/connect",
                follow_redirects=False,
            )
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_oauth_config, None)

    def test_connect_unconfigured_provider_returns_503(self, mock_user):
        """Test connect with unconfigured provider returns 503."""
        mock_config = MagicMock(spec=OAuthConfig)
        mock_config.is_provider_configured.return_value = False

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_oauth_config] = lambda: mock_config

        client = TestClient(app)

        try:
            response = client.get(
                "/oauth/google/connect",
                follow_redirects=False,
            )
            assert response.status_code == 503
            assert "not configured" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_oauth_config, None)


# ============================================================================
# GET /oauth/connections Tests
# ============================================================================


class TestListConnectionsEndpoint:
    """Tests for the GET /oauth/connections endpoint."""

    def test_list_connections_requires_auth(self, unauthenticated_client):
        """Test list connections requires authentication."""
        response = unauthenticated_client.get("/oauth/connections")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, mock_user, mock_repository):
        """Test list connections returns empty list."""
        # Create user first
        await mock_repository.get_or_create(mock_user["uid"], mock_user["email"])

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_repository] = lambda: mock_repository

        client = TestClient(app)

        try:
            response = client.get("/oauth/connections")
            assert response.status_code == 200
            assert response.json()["connections"] == []
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_repository, None)

    @pytest.mark.asyncio
    async def test_list_connections_with_providers(self, mock_user, mock_repository):
        """Test list connections returns connected providers."""
        await mock_repository.get_or_create(mock_user["uid"], mock_user["email"])
        await mock_repository.save_token(
            mock_user["uid"], "google", {"access_token": "test"}
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_repository] = lambda: mock_repository

        client = TestClient(app)

        try:
            response = client.get("/oauth/connections")
            assert response.status_code == 200
            assert "google" in response.json()["connections"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_repository, None)


# ============================================================================
# DELETE /oauth/{provider} Tests
# ============================================================================


class TestDisconnectEndpoint:
    """Tests for the DELETE /oauth/{provider} endpoint."""

    def test_disconnect_requires_auth(self, unauthenticated_client):
        """Test disconnect requires authentication."""
        response = unauthenticated_client.delete("/oauth/google")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_disconnect_not_connected_returns_404(
        self, mock_user, mock_oauth_config, mock_repository
    ):
        """Test disconnect when not connected returns 404."""
        await mock_repository.get_or_create(mock_user["uid"], mock_user["email"])

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config
        app.dependency_overrides[get_repository] = lambda: mock_repository

        client = TestClient(app)

        try:
            response = client.delete("/oauth/google")
            assert response.status_code == 404
            assert "No connection found" in response.json()["detail"]
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_oauth_config, None)
            app.dependency_overrides.pop(get_repository, None)

    @pytest.mark.asyncio
    async def test_disconnect_success(
        self, mock_user, mock_oauth_config, mock_repository
    ):
        """Test successful disconnect."""
        await mock_repository.get_or_create(mock_user["uid"], mock_user["email"])
        await mock_repository.save_token(
            mock_user["uid"], "google", {"access_token": "test"}
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config
        app.dependency_overrides[get_repository] = lambda: mock_repository

        client = TestClient(app)

        try:
            response = client.delete("/oauth/google")
            assert response.status_code == 200
            assert response.json()["status"] == "success"

            # Verify token is deleted
            token = await mock_repository.get_token(mock_user["uid"], "google")
            assert token is None
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_oauth_config, None)
            app.dependency_overrides.pop(get_repository, None)

    def test_disconnect_unknown_provider_returns_404(
        self, mock_user, mock_oauth_config
    ):
        """Test disconnect with unknown provider returns 404."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_oauth_config] = lambda: mock_oauth_config

        client = TestClient(app)

        try:
            response = client.delete("/oauth/unknown")
            assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_oauth_config, None)
