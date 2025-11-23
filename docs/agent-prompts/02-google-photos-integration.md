# Agent Task: Implement Google Photos Integration

## Context

You are working on a FastAPI application where users authenticate via Magic Link and can connect their Google account via OAuth2. The OAuth2 foundation is complete - tokens are stored in `UserRepository`. Your task is to implement the Google Photos integration that uses these tokens.

## Architecture Overview

```
User authenticated (Magic Link)
        ↓
Connect Google (/oauth/google/connect)
        ↓
Tokens stored in UserRepository
        ↓
Google Photos Service (your task) ← uses stored tokens
        ↓
API endpoints for photo operations
```

## Your Task

Implement Google Photos integration in `app/integrations/google/`:
1. Service class to interact with Google Photos API
2. Token refresh handling (using authlib)
3. API endpoints for photo operations
4. Error handling for expired/revoked tokens

## Files to Read First

1. `app/oauth/config.py` - OAuth registry and Google configuration
2. `app/oauth/router.py` - How OAuth flow works
3. `app/users/repository.py` - How to get stored tokens
4. `app/users/models.py` - OAuthToken model
5. `AGENTS.md` - Project conventions

## Implementation Structure

```
app/integrations/google/
├── __init__.py          # (exists)
├── config.py            # Google-specific configuration
├── service.py           # GooglePhotosService class
├── router.py            # API endpoints
└── models.py            # Request/response models
```

## Step 1: Update OAuth Scopes

Edit `app/oauth/config.py` to include Google Photos scope:

```python
oauth.register(
    name="google",
    # ... existing config ...
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/photoslibrary.readonly https://www.googleapis.com/auth/photoslibrary.appendonly",
    },
)
```

## Step 2: Create Google Photos Service

`app/integrations/google/service.py`:

```python
import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.users.models import OAuthToken
from app.oauth.config import get_oauth_config

class GooglePhotosService:
    """Service for interacting with Google Photos API."""

    BASE_URL = "https://photoslibrary.googleapis.com/v1"

    def __init__(self, token: OAuthToken):
        self._token = token
        self._config = get_oauth_config()

    async def _get_client(self) -> AsyncOAuth2Client:
        """Create authenticated HTTP client with token refresh."""
        client = AsyncOAuth2Client(
            client_id=self._config.google_client_id,
            client_secret=self._config.google_client_secret,
            token=self._token.to_authlib_token(),
            token_endpoint="https://oauth2.googleapis.com/token",
        )
        return client

    async def list_albums(self, page_size: int = 20, page_token: str | None = None) -> dict:
        """List user's Google Photos albums."""
        async with await self._get_client() as client:
            params = {"pageSize": page_size}
            if page_token:
                params["pageToken"] = page_token
            response = await client.get(f"{self.BASE_URL}/albums", params=params)
            response.raise_for_status()
            return response.json()

    async def get_album(self, album_id: str) -> dict:
        """Get a specific album."""
        async with await self._get_client() as client:
            response = await client.get(f"{self.BASE_URL}/albums/{album_id}")
            response.raise_for_status()
            return response.json()

    async def create_album(self, title: str) -> dict:
        """Create a new album."""
        async with await self._get_client() as client:
            response = await client.post(
                f"{self.BASE_URL}/albums",
                json={"album": {"title": title}}
            )
            response.raise_for_status()
            return response.json()

    async def upload_media(self, file_bytes: bytes, filename: str) -> str:
        """Upload media and return upload token."""
        async with await self._get_client() as client:
            response = await client.post(
                "https://photoslibrary.googleapis.com/v1/uploads",
                content=file_bytes,
                headers={
                    "Content-Type": "application/octet-stream",
                    "X-Goog-Upload-File-Name": filename,
                    "X-Goog-Upload-Protocol": "raw",
                }
            )
            response.raise_for_status()
            return response.text  # Returns upload token

    async def create_media_item(self, upload_token: str, album_id: str | None = None) -> dict:
        """Create media item from upload token."""
        body = {
            "newMediaItems": [{
                "simpleMediaItem": {"uploadToken": upload_token}
            }]
        }
        if album_id:
            body["albumId"] = album_id

        async with await self._get_client() as client:
            response = await client.post(
                f"{self.BASE_URL}/mediaItems:batchCreate",
                json=body
            )
            response.raise_for_status()
            return response.json()
```

## Step 3: Create API Router

`app/integrations/google/router.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from app.auth.dependencies import get_current_user
from app.users.repository import get_user_repository, UserRepository
from app.integrations.google.service import GooglePhotosService
from app.integrations.google.models import AlbumCreate, AlbumResponse

router = APIRouter(prefix="/integrations/google/photos", tags=["google-photos"])


async def get_google_photos_service(
    user: dict = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> GooglePhotosService:
    """Get GooglePhotosService with user's token."""
    token = await repository.get_token(user["uid"], "google")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google account not connected. Visit /oauth/google/connect first.",
        )
    return GooglePhotosService(token)


@router.get("/albums")
async def list_albums(
    page_size: int = 20,
    page_token: str | None = None,
    service: GooglePhotosService = Depends(get_google_photos_service),
):
    """List user's Google Photos albums."""
    return await service.list_albums(page_size, page_token)


@router.post("/albums")
async def create_album(
    album: AlbumCreate,
    service: GooglePhotosService = Depends(get_google_photos_service),
):
    """Create a new album."""
    return await service.create_album(album.title)


@router.post("/upload")
async def upload_photo(
    file: UploadFile,
    album_id: str | None = None,
    service: GooglePhotosService = Depends(get_google_photos_service),
):
    """Upload a photo to Google Photos."""
    content = await file.read()
    upload_token = await service.upload_media(content, file.filename)
    result = await service.create_media_item(upload_token, album_id)
    return result
```

## Step 4: Create Models

`app/integrations/google/models.py`:

```python
from pydantic import BaseModel

class AlbumCreate(BaseModel):
    title: str

class AlbumResponse(BaseModel):
    id: str
    title: str
    productUrl: str | None = None
    mediaItemsCount: str | None = None
```

## Step 5: Wire Router

Update `app/main.py`:

```python
from app.integrations.google import router as google_router
# ...
app.include_router(google_router.router)
```

## Token Refresh Handling

Authlib's `AsyncOAuth2Client` handles token refresh automatically when:
1. Token has `refresh_token`
2. `token_endpoint` is configured
3. Token is expired

After refresh, update stored token:

```python
async def _get_client(self) -> AsyncOAuth2Client:
    client = AsyncOAuth2Client(
        # ... config ...
        update_token=self._on_token_refresh,  # Callback for token refresh
    )
    return client

async def _on_token_refresh(self, token: dict, refresh_token: str = None, access_token: str = None):
    """Called when token is refreshed - update storage."""
    # Note: Need access to repository and user_uid here
    # Consider passing these to __init__
    pass
```

## Error Handling

Handle common Google API errors:

```python
from httpx import HTTPStatusError

class GooglePhotosError(Exception):
    """Base exception for Google Photos errors."""
    pass

class TokenExpiredError(GooglePhotosError):
    """Token expired and couldn't be refreshed."""
    pass

class QuotaExceededError(GooglePhotosError):
    """API quota exceeded."""
    pass

# In service methods:
try:
    response = await client.get(...)
except HTTPStatusError as e:
    if e.response.status_code == 401:
        raise TokenExpiredError("Google token expired")
    if e.response.status_code == 429:
        raise QuotaExceededError("API quota exceeded")
    raise
```

## Testing Requirements

Create `tests/integrations/test_google_photos.py`:

1. Mock Google Photos API responses
2. Test album CRUD operations
3. Test photo upload flow
4. Test token refresh handling
5. Test error scenarios (401, 429, etc.)

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/integrations/google/photos/albums` | GET | List albums |
| `/integrations/google/photos/albums` | POST | Create album |
| `/integrations/google/photos/upload` | POST | Upload photo |

## Success Criteria

1. Can list user's Google Photos albums
2. Can create new albums
3. Can upload photos to albums
4. Token refresh works automatically
5. Proper error handling for API failures
6. Tests pass with mocked API

## Do NOT

- Store Google credentials in code
- Skip token validation
- Ignore rate limiting
- Modify OAuth flow (it's complete)
- Change UserRepository interface
