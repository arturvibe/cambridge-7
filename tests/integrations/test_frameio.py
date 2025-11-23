import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC

from app.integrations.adobe.service import (
    FrameioService,
    FrameioAuthError,
    FrameioNotFoundError,
    FrameioRateLimitError,
)
from app.users.models import OAuthToken, User
from app.users.repository import InMemoryUserRepository


class TestFrameioService:
    @pytest.fixture
    def valid_token(self):
        return OAuthToken(
            provider="adobe",
            access_token="valid-access-token",
            refresh_token="valid-refresh-token",
            expires_at=int((datetime.now(UTC) + timedelta(hours=1)).timestamp()),
        )

    @pytest.fixture
    def expired_token(self):
        return OAuthToken(
            provider="adobe",
            access_token="expired-access-token",
            refresh_token="valid-refresh-token",
            expires_at=int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
        )

    @pytest.fixture
    def user_repository(self):
        return InMemoryUserRepository()

    @pytest.fixture
    def frameio_service(self, valid_token, user_repository):
        # Create user in repo
        return FrameioService(
            token=valid_token, user_uid="test-uid", repository=user_repository
        )

    @pytest.mark.asyncio
    async def test_get_me(self, frameio_service):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "user-123",
                "email": "test@example.com",
            }
            mock_request.return_value = mock_response

            result = await frameio_service.get_me()

            assert result["id"] == "user-123"
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "GET"
            assert kwargs["headers"]["Authorization"] == "Bearer valid-access-token"
            assert args[1].endswith("/me")

    @pytest.mark.asyncio
    async def test_list_accounts(self, frameio_service):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [{"id": "acc-1"}]
            mock_request.return_value = mock_response

            result = await frameio_service.list_accounts()

            assert len(result) == 1
            assert result[0]["id"] == "acc-1"

    @pytest.mark.asyncio
    async def test_create_comment(self, frameio_service):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "comment-1"}
            mock_request.return_value = mock_response

            await frameio_service.create_comment("asset-1", "Nice shot", 10.5)

            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert kwargs["json"] == {"text": "Nice shot", "timestamp": 10.5}

    @pytest.mark.asyncio
    async def test_token_refresh_success(self, expired_token, user_repository):
        # Mock config to have client secrets
        with patch("app.integrations.adobe.service.get_oauth_config") as mock_config:
            mock_config.return_value.adobe_client_id = "client-id"
            mock_config.return_value.adobe_client_secret = "client-secret"

            # Create user for repository persistence
            await user_repository.create(User(uid="test-uid", email="test@example.com"))

            service = FrameioService(
                token=expired_token, user_uid="test-uid", repository=user_repository
            )

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "access_token": "new-access-token",
                    "refresh_token": "new-refresh-token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                }
                mock_post.return_value = mock_response

                # Trigger refresh
                new_token = await service.refresh_token_if_needed()

                assert new_token.access_token == "new-access-token"
                assert service._token.access_token == "new-access-token"

                # Verify API call
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["data"]["grant_type"] == "refresh_token"
                assert call_kwargs["data"]["refresh_token"] == "valid-refresh-token"

                # Verify persistence
                saved_token = await user_repository.get_token("test-uid", "adobe")
                assert saved_token.access_token == "new-access-token"

    @pytest.mark.asyncio
    async def test_token_refresh_failure(self, expired_token, user_repository):
        with patch("app.integrations.adobe.service.get_oauth_config") as mock_config:
            mock_config.return_value.adobe_client_id = "client-id"
            mock_config.return_value.adobe_client_secret = "client-secret"

            service = FrameioService(
                token=expired_token, user_uid="test-uid", repository=user_repository
            )

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "invalid_grant"
                mock_post.return_value = mock_response

                with pytest.raises(FrameioAuthError):
                    await service.refresh_token_if_needed()

    @pytest.mark.asyncio
    async def test_error_not_found(self, frameio_service):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_request.return_value = mock_response

            with pytest.raises(FrameioNotFoundError):
                await frameio_service.get_asset("missing")

    @pytest.mark.asyncio
    async def test_error_rate_limit(self, frameio_service):
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_request.return_value = mock_response

            with pytest.raises(FrameioRateLimitError):
                await frameio_service.get_asset("anything")
