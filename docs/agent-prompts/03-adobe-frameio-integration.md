# Agent Task: Implement Adobe Frame.io Integration

## Context

You are working on a FastAPI application where users authenticate via Magic Link and can connect their Adobe account via OAuth2. The OAuth2 foundation is complete - tokens are stored in `UserRepository`. Your task is to implement the Adobe Frame.io integration that uses these tokens.

The app already receives Frame.io webhooks (existing feature). This integration enables the app to call Frame.io API on behalf of authenticated users.

## Architecture Overview

```
User authenticated (Magic Link)
        ↓
Connect Adobe (/oauth/adobe/connect)
        ↓
Tokens stored in UserRepository
        ↓
Frame.io Service (your task) ← uses stored tokens
        ↓
API endpoints for Frame.io operations
```

## Your Task

Implement Adobe Frame.io integration in `app/integrations/adobe/`:
1. Service class to interact with Frame.io API
2. Token refresh handling
3. API endpoints for Frame.io operations
4. Correlation with incoming webhooks

## Files to Read First

1. `app/oauth/config.py` - OAuth registry and Adobe configuration
2. `app/api/frameio.py` - Existing webhook receiver
3. `app/core/domain.py` - FrameIOEvent model
4. `app/users/repository.py` - How to get stored tokens
5. `AGENTS.md` - Project conventions

## Implementation Structure

```
app/integrations/adobe/
├── __init__.py          # (exists)
├── config.py            # Frame.io API configuration
├── service.py           # FrameioService class
├── router.py            # API endpoints
└── models.py            # Request/response models
```

## Step 1: Update OAuth Configuration

Edit `app/oauth/config.py` to configure Adobe OAuth properly:

```python
oauth.register(
    name="adobe",
    client_id=config.adobe_client_id,
    client_secret=config.adobe_client_secret,
    authorize_url="https://ims-na1.adobelogin.com/ims/authorize/v2",
    access_token_url="https://ims-na1.adobelogin.com/ims/token/v3",
    client_kwargs={
        "scope": "openid email profile frame.io.read frame.io.write",
    },
)
```

## Step 2: Create Frame.io Service

`app/integrations/adobe/service.py`:

```python
import httpx
from app.users.models import OAuthToken

class FrameioService:
    """Service for interacting with Frame.io API v2."""

    BASE_URL = "https://api.frame.io/v2"

    def __init__(self, token: OAuthToken):
        self._token = token

    def _get_headers(self) -> dict:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self._token.access_token}",
            "Content-Type": "application/json",
        }

    async def get_me(self) -> dict:
        """Get current user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/me",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_accounts(self) -> list[dict]:
        """List user's Frame.io accounts."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_projects(self, account_id: str) -> list[dict]:
        """List projects in an account."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/accounts/{account_id}/projects",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_project(self, project_id: str) -> dict:
        """Get project details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/projects/{project_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_asset(self, asset_id: str) -> dict:
        """Get asset (file) details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/assets/{asset_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def list_assets(self, folder_id: str) -> list[dict]:
        """List assets in a folder."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/assets/{folder_id}/children",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def create_comment(self, asset_id: str, text: str, timestamp: float | None = None) -> dict:
        """Create a comment on an asset."""
        body = {"text": text}
        if timestamp is not None:
            body["timestamp"] = timestamp

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/assets/{asset_id}/comments",
                headers=self._get_headers(),
                json=body,
            )
            response.raise_for_status()
            return response.json()

    async def get_download_url(self, asset_id: str) -> str:
        """Get download URL for an asset."""
        asset = await self.get_asset(asset_id)
        return asset.get("original")

    async def create_upload_url(self, parent_id: str, filename: str, filesize: int) -> dict:
        """Create upload URL for a new asset."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/assets/{parent_id}/children",
                headers=self._get_headers(),
                json={
                    "name": filename,
                    "type": "file",
                    "filesize": filesize,
                },
            )
            response.raise_for_status()
            return response.json()
```

## Step 3: Create API Router

`app/integrations/adobe/router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth.dependencies import get_current_user
from app.users.repository import get_user_repository, UserRepository
from app.integrations.adobe.service import FrameioService
from app.integrations.adobe.models import CommentCreate

router = APIRouter(prefix="/integrations/adobe/frameio", tags=["frameio"])


async def get_frameio_service(
    user: dict = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> FrameioService:
    """Get FrameioService with user's token."""
    token = await repository.get_token(user["uid"], "adobe")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Adobe account not connected. Visit /oauth/adobe/connect first.",
        )
    return FrameioService(token)


@router.get("/me")
async def get_current_frameio_user(
    service: FrameioService = Depends(get_frameio_service),
):
    """Get current Frame.io user info."""
    return await service.get_me()


@router.get("/accounts")
async def list_accounts(
    service: FrameioService = Depends(get_frameio_service),
):
    """List Frame.io accounts."""
    return await service.list_accounts()


@router.get("/accounts/{account_id}/projects")
async def list_projects(
    account_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """List projects in an account."""
    return await service.list_projects(account_id)


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """Get project details."""
    return await service.get_project(project_id)


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """Get asset details."""
    return await service.get_asset(asset_id)


@router.get("/assets/{folder_id}/children")
async def list_assets(
    folder_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """List assets in a folder."""
    return await service.list_assets(folder_id)


@router.post("/assets/{asset_id}/comments")
async def create_comment(
    asset_id: str,
    comment: CommentCreate,
    service: FrameioService = Depends(get_frameio_service),
):
    """Create a comment on an asset."""
    return await service.create_comment(asset_id, comment.text, comment.timestamp)


@router.get("/assets/{asset_id}/download-url")
async def get_download_url(
    asset_id: str,
    service: FrameioService = Depends(get_frameio_service),
):
    """Get download URL for an asset."""
    url = await service.get_download_url(asset_id)
    return {"download_url": url}
```

## Step 4: Create Models

`app/integrations/adobe/models.py`:

```python
from pydantic import BaseModel

class CommentCreate(BaseModel):
    text: str
    timestamp: float | None = None  # For video timecode comments

class AssetResponse(BaseModel):
    id: str
    name: str
    type: str
    filesize: int | None = None
    original: str | None = None  # Download URL

class ProjectResponse(BaseModel):
    id: str
    name: str
    root_asset_id: str
```

## Step 5: Wire Router

Update `app/main.py`:

```python
from app.integrations.adobe import router as adobe_router
# ...
app.include_router(adobe_router.router)
```

## Webhook Correlation (Advanced)

Link incoming webhooks to user actions:

```python
# In webhook handler or separate service
async def handle_file_ready_webhook(event: FrameIOEvent, repository: UserRepository):
    """
    When a file is ready, we can correlate with connected users.

    Use case: Notify user when their uploaded file finishes processing.
    """
    # Find users connected to this Frame.io account
    # This requires storing the Frame.io account_id with the user
    pass
```

## Token Refresh

Adobe tokens expire. Implement refresh:

```python
async def refresh_token_if_needed(self) -> OAuthToken:
    """Refresh token if expired."""
    if not self._token.is_expired():
        return self._token

    if not self._token.refresh_token:
        raise TokenExpiredError("Token expired and no refresh token available")

    # Use authlib for refresh
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://ims-na1.adobelogin.com/ims/token/v3",
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._token.refresh_token,
                "client_id": self._config.adobe_client_id,
                "client_secret": self._config.adobe_client_secret,
            },
        )
        response.raise_for_status()
        new_token_data = response.json()

        # Update stored token
        return OAuthToken.from_oauth_response("adobe", new_token_data)
```

## Error Handling

```python
class FrameioError(Exception):
    """Base exception for Frame.io errors."""
    pass

class FrameioAuthError(FrameioError):
    """Authentication/authorization error."""
    pass

class FrameioNotFoundError(FrameioError):
    """Resource not found."""
    pass

class FrameioRateLimitError(FrameioError):
    """Rate limit exceeded."""
    pass

# In service methods, catch and re-raise appropriately
```

## Testing Requirements

Create `tests/integrations/test_frameio.py`:

1. Mock Frame.io API responses
2. Test account/project/asset listing
3. Test comment creation
4. Test error handling (401, 404, 429)
5. Test token refresh flow

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integrations/adobe/frameio/me` | GET | Current user info |
| `/integrations/adobe/frameio/accounts` | GET | List accounts |
| `/integrations/adobe/frameio/accounts/{id}/projects` | GET | List projects |
| `/integrations/adobe/frameio/projects/{id}` | GET | Project details |
| `/integrations/adobe/frameio/assets/{id}` | GET | Asset details |
| `/integrations/adobe/frameio/assets/{id}/children` | GET | List folder contents |
| `/integrations/adobe/frameio/assets/{id}/comments` | POST | Create comment |
| `/integrations/adobe/frameio/assets/{id}/download-url` | GET | Get download URL |

## Success Criteria

1. Can authenticate with Frame.io using stored OAuth token
2. Can list accounts, projects, and assets
3. Can create comments on assets
4. Can get download URLs
5. Token refresh works when expired
6. Proper error handling
7. Tests pass with mocked API

## Do NOT

- Store Adobe credentials in code
- Modify webhook receiver (it's separate)
- Change OAuth flow
- Skip error handling
- Ignore rate limits
