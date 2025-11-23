"""
Tests for Frame.io integration.

Tests the FrameioService, router endpoints, and error handling.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

# Set environment variables before importing app
with patch.dict(
    os.environ,
    {
        "GCP_PROJECT_ID": "test-project",
        "FIREBASE_WEB_API_KEY": "test-api-key",
        "BASE_URL": "http://localhost:8080",
        "ADOBE_CLIENT_ID": "test-adobe-id",
        "ADOBE_CLIENT_SECRET": "test-adobe-secret",
    },
):
    from app.main import app
    from app.auth.dependencies import get_current_user
    from app.integrations.adobe.config import FrameioConfig
    from app.integrations.adobe.exceptions import (
        FrameioAuthError,
        FrameioError,
        FrameioNotFoundError,
        FrameioRateLimitError,
        TokenExpiredError,
    )
    from app.integrations.adobe.router import get_frameio_service
    from app.integrations.adobe.service import FrameioService
    from app.users.models import OAuthToken
    from app.users.repository import (
        InMemoryUserRepository,
        get_user_repository,
    )


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
def mock_token():
    """Mock OAuth token for Adobe."""
    return OAuthToken(
        provider="adobe",
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        expires_at=9999999999,  # Far future
        token_type="Bearer",
        scope="openid email profile frame.io.read frame.io.write",
    )


@pytest.fixture
def expired_token():
    """Mock expired OAuth token."""
    return OAuthToken(
        provider="adobe",
        access_token="expired-access-token",
        refresh_token="test-refresh-token",
        expires_at=1,  # Past
        token_type="Bearer",
    )


@pytest.fixture
def frameio_config():
    """Mock Frame.io configuration."""
    return FrameioConfig(
        base_url="https://api.frame.io/v2",
        token_refresh_url="https://ims-na1.adobelogin.com/ims/token/v3",
        adobe_client_id="test-adobe-id",
        adobe_client_secret="test-adobe-secret",
    )


@pytest.fixture
def mock_repository():
    """Mock user repository."""
    return InMemoryUserRepository()


# ============================================================================
# FrameioService Tests
# ============================================================================


class TestFrameioService:
    """Tests for the FrameioService class."""

    @pytest.mark.asyncio
    async def test_get_me_success(self, mock_token, frameio_config):
        """Test successful get_me call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={"id": "user-123", "email": "test@example.com", "name": "Test User"},
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.get_me()

        assert result["id"] == "user-123"
        assert result["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_list_accounts_success(self, mock_token, frameio_config):
        """Test successful list_accounts call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json=[
                {"id": "account-1", "name": "Account 1"},
                {"id": "account-2", "name": "Account 2"},
            ],
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.list_accounts()

        assert len(result) == 2
        assert result[0]["id"] == "account-1"

    @pytest.mark.asyncio
    async def test_list_projects_success(self, mock_token, frameio_config):
        """Test successful list_projects call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json=[
                {"id": "proj-1", "name": "Project 1", "root_asset_id": "root-1"},
            ],
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.list_projects("account-123")

        assert len(result) == 1
        assert result[0]["id"] == "proj-1"

    @pytest.mark.asyncio
    async def test_get_project_success(self, mock_token, frameio_config):
        """Test successful get_project call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={"id": "proj-1", "name": "Project 1", "root_asset_id": "root-1"},
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.get_project("proj-1")

        assert result["id"] == "proj-1"
        assert result["name"] == "Project 1"

    @pytest.mark.asyncio
    async def test_get_asset_success(self, mock_token, frameio_config):
        """Test successful get_asset call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={
                "id": "asset-1",
                "name": "video.mp4",
                "type": "file",
                "filesize": 1024000,
                "original": "https://download.url/video.mp4",
            },
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.get_asset("asset-1")

        assert result["id"] == "asset-1"
        assert result["type"] == "file"

    @pytest.mark.asyncio
    async def test_list_assets_success(self, mock_token, frameio_config):
        """Test successful list_assets call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json=[
                {"id": "asset-1", "name": "file1.mp4", "type": "file"},
                {"id": "asset-2", "name": "folder", "type": "folder"},
            ],
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.list_assets("folder-123")

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_create_comment_success(self, mock_token, frameio_config):
        """Test successful create_comment call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={"id": "comment-1", "text": "Great work!", "timestamp": 10.5},
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.create_comment("asset-1", "Great work!", 10.5)

        assert result["id"] == "comment-1"
        assert result["text"] == "Great work!"

    @pytest.mark.asyncio
    async def test_get_download_url_success(self, mock_token, frameio_config):
        """Test successful get_download_url call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={
                "id": "asset-1",
                "name": "video.mp4",
                "original": "https://download.url/video.mp4",
            },
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.get_download_url("asset-1")

        assert result == "https://download.url/video.mp4"

    @pytest.mark.asyncio
    async def test_create_upload_url_success(self, mock_token, frameio_config):
        """Test successful create_upload_url call."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(
            200,
            json={
                "id": "new-asset-1",
                "name": "upload.mp4",
                "upload_url": "https://upload.url/video.mp4",
            },
        )

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            result = await service.create_upload_url("folder-1", "upload.mp4", 1024000)

        assert result["id"] == "new-asset-1"


class TestFrameioServiceErrors:
    """Tests for FrameioService error handling."""

    @pytest.mark.asyncio
    async def test_unauthorized_error(self, mock_token, frameio_config):
        """Test 401 error raises FrameioAuthError."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(401, json={"error": "Unauthorized"})

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            with pytest.raises(FrameioAuthError):
                await service.get_me()

    @pytest.mark.asyncio
    async def test_forbidden_error(self, mock_token, frameio_config):
        """Test 403 error raises FrameioAuthError."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(403, json={"error": "Forbidden"})

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            with pytest.raises(FrameioAuthError):
                await service.get_me()

    @pytest.mark.asyncio
    async def test_not_found_error(self, mock_token, frameio_config):
        """Test 404 error raises FrameioNotFoundError."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(404, json={"error": "Not Found"})

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            with pytest.raises(FrameioNotFoundError):
                await service.get_asset("nonexistent")

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_token, frameio_config):
        """Test 429 error raises FrameioRateLimitError."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(429, json={"error": "Rate Limited"})

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            with pytest.raises(FrameioRateLimitError):
                await service.list_accounts()

    @pytest.mark.asyncio
    async def test_generic_error(self, mock_token, frameio_config):
        """Test other errors raise FrameioError."""
        service = FrameioService(mock_token, config=frameio_config)

        mock_response = httpx.Response(500, text="Internal Server Error")

        with patch("httpx.AsyncClient.request", return_value=mock_response):
            with pytest.raises(FrameioError):
                await service.get_me()


class TestFrameioServiceTokenRefresh:
    """Tests for token refresh functionality."""

    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(self, expired_token, frameio_config):
        """Test token refresh when access token is expired."""
        refresh_callback = AsyncMock()
        service = FrameioService(
            expired_token,
            config=frameio_config,
            on_token_refresh=refresh_callback,
        )

        # Mock token refresh response
        refresh_response = httpx.Response(
            200,
            json={
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_at": 9999999999,
            },
        )

        # Mock API response after refresh
        api_response = httpx.Response(
            200,
            json={"id": "user-123", "email": "test@example.com"},
        )

        with patch("httpx.AsyncClient.post", return_value=refresh_response):
            with patch("httpx.AsyncClient.request", return_value=api_response):
                result = await service.get_me()

        assert result["id"] == "user-123"
        refresh_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_token_refresh_no_refresh_token(self, frameio_config):
        """Test error when token expired and no refresh token."""
        token = OAuthToken(
            provider="adobe",
            access_token="expired-token",
            refresh_token=None,  # No refresh token
            expires_at=1,
        )
        service = FrameioService(token, config=frameio_config)

        with pytest.raises(TokenExpiredError):
            await service.get_me()

    @pytest.mark.asyncio
    async def test_token_refresh_no_credentials(self, expired_token):
        """Test error when credentials not configured for refresh."""
        config = FrameioConfig(
            adobe_client_id=None,  # No credentials
            adobe_client_secret=None,
        )
        service = FrameioService(expired_token, config=config)

        with pytest.raises(TokenExpiredError):
            await service.get_me()


# ============================================================================
# Router Tests
# ============================================================================


class TestFrameioRouterEndpoints:
    """Tests for Frame.io router endpoints."""

    @pytest.fixture
    def authenticated_client_with_adobe(self, mock_user, mock_repository, mock_token):
        """Test client with mocked authentication and Adobe token."""

        async def get_repo():
            return mock_repository

        # Create mock service
        mock_service = MagicMock(spec=FrameioService)
        mock_service.get_me = AsyncMock(
            return_value={"id": "user-123", "email": "test@example.com"}
        )
        mock_service.list_accounts = AsyncMock(
            return_value=[{"id": "acc-1", "name": "Account 1"}]
        )
        mock_service.list_projects = AsyncMock(
            return_value=[{"id": "proj-1", "name": "Project 1"}]
        )
        mock_service.get_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Project 1"}
        )
        mock_service.get_asset = AsyncMock(
            return_value={"id": "asset-1", "name": "video.mp4", "type": "file"}
        )
        mock_service.list_assets = AsyncMock(
            return_value=[{"id": "asset-1", "name": "video.mp4", "type": "file"}]
        )
        mock_service.create_comment = AsyncMock(
            return_value={"id": "comment-1", "text": "Nice!"}
        )
        mock_service.get_download_url = AsyncMock(
            return_value="https://download.url/video.mp4"
        )

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_user_repository] = get_repo
        app.dependency_overrides[get_frameio_service] = lambda: mock_service

        client = TestClient(app)
        yield client, mock_service

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repository, None)
        app.dependency_overrides.pop(get_frameio_service, None)

    def test_get_me_requires_auth(self):
        """Test /me endpoint requires authentication."""
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        response = client.get("/integrations/adobe/frameio/me")
        assert response.status_code == 401

    def test_get_me_success(self, authenticated_client_with_adobe):
        """Test successful /me endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/me")
        assert response.status_code == 200
        assert response.json()["id"] == "user-123"
        mock_service.get_me.assert_called_once()

    def test_list_accounts_success(self, authenticated_client_with_adobe):
        """Test successful /accounts endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/accounts")
        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_service.list_accounts.assert_called_once()

    def test_list_projects_success(self, authenticated_client_with_adobe):
        """Test successful /accounts/{id}/projects endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/accounts/acc-1/projects")
        assert response.status_code == 200
        mock_service.list_projects.assert_called_once_with("acc-1")

    def test_get_project_success(self, authenticated_client_with_adobe):
        """Test successful /projects/{id} endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/projects/proj-1")
        assert response.status_code == 200
        mock_service.get_project.assert_called_once_with("proj-1")

    def test_get_asset_success(self, authenticated_client_with_adobe):
        """Test successful /assets/{id} endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/assets/asset-1")
        assert response.status_code == 200
        mock_service.get_asset.assert_called_once_with("asset-1")

    def test_list_assets_success(self, authenticated_client_with_adobe):
        """Test successful /assets/{id}/children endpoint."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/assets/folder-1/children")
        assert response.status_code == 200
        mock_service.list_assets.assert_called_once_with("folder-1")

    def test_create_comment_success(self, authenticated_client_with_adobe):
        """Test successful comment creation."""
        client, mock_service = authenticated_client_with_adobe
        response = client.post(
            "/integrations/adobe/frameio/assets/asset-1/comments",
            json={"text": "Nice!", "timestamp": 10.5},
        )
        assert response.status_code == 200
        mock_service.create_comment.assert_called_once_with("asset-1", "Nice!", 10.5)

    def test_create_comment_without_timestamp(self, authenticated_client_with_adobe):
        """Test comment creation without timestamp."""
        client, mock_service = authenticated_client_with_adobe
        response = client.post(
            "/integrations/adobe/frameio/assets/asset-1/comments",
            json={"text": "Nice!"},
        )
        assert response.status_code == 200
        mock_service.create_comment.assert_called_once_with("asset-1", "Nice!", None)

    def test_get_download_url_success(self, authenticated_client_with_adobe):
        """Test successful download URL retrieval."""
        client, mock_service = authenticated_client_with_adobe
        response = client.get("/integrations/adobe/frameio/assets/asset-1/download-url")
        assert response.status_code == 200
        assert response.json()["download_url"] == "https://download.url/video.mp4"


class TestFrameioRouterErrors:
    """Tests for Frame.io router error handling."""

    @pytest.fixture
    def error_client(self, mock_user):
        """Test client that raises Frame.io errors."""
        mock_service = MagicMock(spec=FrameioService)
        mock_service.get_me = AsyncMock(side_effect=FrameioAuthError("Auth failed"))
        mock_service.get_asset = AsyncMock(
            side_effect=FrameioNotFoundError("Not found")
        )
        mock_service.list_accounts = AsyncMock(
            side_effect=FrameioRateLimitError("Rate limited")
        )
        mock_service.get_project = AsyncMock(side_effect=FrameioError("API error"))

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_frameio_service] = lambda: mock_service

        client = TestClient(app)
        yield client

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_frameio_service, None)

    def test_auth_error_returns_401(self, error_client):
        """Test auth error returns 401."""
        response = error_client.get("/integrations/adobe/frameio/me")
        assert response.status_code == 401

    def test_not_found_error_returns_404(self, error_client):
        """Test not found error returns 404."""
        response = error_client.get("/integrations/adobe/frameio/assets/missing")
        assert response.status_code == 404

    def test_rate_limit_error_returns_429(self, error_client):
        """Test rate limit error returns 429."""
        response = error_client.get("/integrations/adobe/frameio/accounts")
        assert response.status_code == 429

    def test_generic_error_returns_502(self, error_client):
        """Test generic error returns 502."""
        response = error_client.get("/integrations/adobe/frameio/projects/proj-1")
        assert response.status_code == 502


class TestFrameioRouterNoAdobeConnection:
    """Tests for router when Adobe is not connected."""

    @pytest.fixture
    def client_without_adobe(self, mock_user, mock_repository):
        """Test client without Adobe connection."""

        async def get_repo():
            return mock_repository

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_user_repository] = get_repo
        # Don't override get_frameio_service, let it use the real dependency

        client = TestClient(app)
        yield client

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repository, None)

    def test_no_adobe_connection_returns_403(self, client_without_adobe):
        """Test 403 when Adobe not connected."""
        response = client_without_adobe.get("/integrations/adobe/frameio/me")
        assert response.status_code == 403
        assert "Adobe account not connected" in response.json()["detail"]


# ============================================================================
# Config Tests
# ============================================================================


class TestFrameioConfig:
    """Tests for Frame.io configuration."""

    def test_config_from_env(self):
        """Test configuration loads from environment."""
        with patch.dict(
            os.environ,
            {
                "ADOBE_CLIENT_ID": "test-id",
                "ADOBE_CLIENT_SECRET": "test-secret",
            },
        ):
            config = FrameioConfig.from_env()
            assert config.adobe_client_id == "test-id"
            assert config.adobe_client_secret == "test-secret"

    def test_can_refresh_tokens_true(self):
        """Test can_refresh_tokens returns True when credentials set."""
        config = FrameioConfig(
            adobe_client_id="id",
            adobe_client_secret="secret",
        )
        assert config.can_refresh_tokens() is True

    def test_can_refresh_tokens_false(self):
        """Test can_refresh_tokens returns False when credentials missing."""
        config = FrameioConfig(
            adobe_client_id=None,
            adobe_client_secret=None,
        )
        assert config.can_refresh_tokens() is False


# ============================================================================
# Models Tests
# ============================================================================


class TestFrameioModels:
    """Tests for Frame.io models."""

    def test_comment_create_with_timestamp(self):
        """Test CommentCreate model with timestamp."""
        from app.integrations.adobe.models import CommentCreate

        comment = CommentCreate(text="Great video!", timestamp=10.5)
        assert comment.text == "Great video!"
        assert comment.timestamp == 10.5

    def test_comment_create_without_timestamp(self):
        """Test CommentCreate model without timestamp."""
        from app.integrations.adobe.models import CommentCreate

        comment = CommentCreate(text="Great video!")
        assert comment.text == "Great video!"
        assert comment.timestamp is None

    def test_download_url_response(self):
        """Test DownloadUrlResponse model."""
        from app.integrations.adobe.models import DownloadUrlResponse

        response = DownloadUrlResponse(download_url="https://example.com/video.mp4")
        assert response.download_url == "https://example.com/video.mp4"
