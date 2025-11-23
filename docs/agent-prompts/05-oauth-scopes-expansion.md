# Agent Task: Implement Dynamic OAuth Scopes

## Context

The OAuth2 foundation uses fixed scopes configured at startup. Different features may require different scopes (e.g., Google Photos needs different scopes than Google Drive). Your task is to implement dynamic scope management.

## Current State

```python
# app/oauth/config.py - Fixed scopes
oauth.register(
    name="google",
    client_kwargs={"scope": "openid email profile"},  # Fixed
)
```

## Desired State

```python
# User requests specific integration
GET /oauth/google/connect?scopes=photos

# System requests appropriate scopes
→ "openid email https://www.googleapis.com/auth/photoslibrary"
```

## Your Task

1. Create scope definitions per integration
2. Allow scope selection during OAuth connect
3. Store granted scopes with tokens
4. Validate required scopes before API calls

## Implementation

### Step 1: Define Scope Registry

`app/oauth/scopes.py`:

```python
"""
OAuth scope definitions for each provider and integration.
"""

from dataclasses import dataclass
from enum import Enum


class GoogleScope(Enum):
    """Google OAuth scopes by feature."""

    # Base scopes (always included)
    OPENID = "openid"
    EMAIL = "email"
    PROFILE = "profile"

    # Google Photos
    PHOTOS_READONLY = "https://www.googleapis.com/auth/photoslibrary.readonly"
    PHOTOS_APPEND = "https://www.googleapis.com/auth/photoslibrary.appendonly"
    PHOTOS_FULL = "https://www.googleapis.com/auth/photoslibrary"

    # Google Drive (future)
    DRIVE_READONLY = "https://www.googleapis.com/auth/drive.readonly"
    DRIVE_FILE = "https://www.googleapis.com/auth/drive.file"


class AdobeScope(Enum):
    """Adobe OAuth scopes by feature."""

    # Base scopes
    OPENID = "openid"
    EMAIL = "email"
    PROFILE = "profile"

    # Frame.io
    FRAMEIO_READ = "frame.io.read"
    FRAMEIO_WRITE = "frame.io.write"


@dataclass
class ScopeSet:
    """Named set of scopes for a specific integration."""

    name: str
    description: str
    scopes: list[str]


# Predefined scope sets for common integrations
GOOGLE_SCOPE_SETS = {
    "basic": ScopeSet(
        name="basic",
        description="Basic profile information",
        scopes=[
            GoogleScope.OPENID.value,
            GoogleScope.EMAIL.value,
            GoogleScope.PROFILE.value,
        ],
    ),
    "photos": ScopeSet(
        name="photos",
        description="Google Photos read and upload",
        scopes=[
            GoogleScope.OPENID.value,
            GoogleScope.EMAIL.value,
            GoogleScope.PHOTOS_READONLY.value,
            GoogleScope.PHOTOS_APPEND.value,
        ],
    ),
    "photos_full": ScopeSet(
        name="photos_full",
        description="Full Google Photos access",
        scopes=[
            GoogleScope.OPENID.value,
            GoogleScope.EMAIL.value,
            GoogleScope.PHOTOS_FULL.value,
        ],
    ),
    "drive": ScopeSet(
        name="drive",
        description="Google Drive file access",
        scopes=[
            GoogleScope.OPENID.value,
            GoogleScope.EMAIL.value,
            GoogleScope.DRIVE_FILE.value,
        ],
    ),
}

ADOBE_SCOPE_SETS = {
    "basic": ScopeSet(
        name="basic",
        description="Basic profile information",
        scopes=[
            AdobeScope.OPENID.value,
            AdobeScope.EMAIL.value,
            AdobeScope.PROFILE.value,
        ],
    ),
    "frameio": ScopeSet(
        name="frameio",
        description="Frame.io read and write access",
        scopes=[
            AdobeScope.OPENID.value,
            AdobeScope.EMAIL.value,
            AdobeScope.FRAMEIO_READ.value,
            AdobeScope.FRAMEIO_WRITE.value,
        ],
    ),
}


def get_scope_set(provider: str, name: str) -> ScopeSet:
    """
    Get a predefined scope set.

    Args:
        provider: OAuth provider (google, adobe)
        name: Scope set name (basic, photos, frameio, etc.)

    Returns:
        ScopeSet with scopes for the integration

    Raises:
        ValueError: If provider or scope set not found
    """
    sets = {
        "google": GOOGLE_SCOPE_SETS,
        "adobe": ADOBE_SCOPE_SETS,
    }

    provider_sets = sets.get(provider)
    if not provider_sets:
        raise ValueError(f"Unknown provider: {provider}")

    scope_set = provider_sets.get(name)
    if not scope_set:
        available = list(provider_sets.keys())
        raise ValueError(
            f"Unknown scope set '{name}' for {provider}. "
            f"Available: {available}"
        )

    return scope_set


def get_scope_string(provider: str, name: str) -> str:
    """Get space-separated scope string for OAuth request."""
    scope_set = get_scope_set(provider, name)
    return " ".join(scope_set.scopes)
```

### Step 2: Update OAuth Router

`app/oauth/router.py`:

```python
from app.oauth.scopes import get_scope_string, get_scope_set

@router.get("/{provider}/connect")
async def connect(
    provider: ValidProvider,
    request: Request,
    user: CurrentUser,
    oauth: OAuthRegistry,
    scopes: str = "basic",  # NEW: scope set parameter
):
    """
    Start OAuth2 authorization flow.

    Args:
        provider: OAuth provider name
        scopes: Scope set name (basic, photos, frameio, etc.)
    """
    config = get_oauth_config()
    redirect_uri = config.get_callback_url(provider)

    # Get scope string for requested integration
    try:
        scope_string = get_scope_string(provider, scopes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    logger.info(
        f"Starting OAuth flow for {provider} with scopes: {scopes}",
        extra={"user_uid": user.get("uid"), "scopes": scopes},
    )

    client = oauth.create_client(provider)

    # Override scopes for this request
    return await client.authorize_redirect(
        request,
        redirect_uri,
        scope=scope_string,  # Pass scopes explicitly
    )
```

### Step 3: Store Granted Scopes

Update `app/users/models.py`:

```python
class OAuthToken(BaseModel):
    # ... existing fields ...

    granted_scopes: list[str] = Field(
        default_factory=list,
        description="Scopes that were actually granted",
    )

    def has_scope(self, scope: str) -> bool:
        """Check if a specific scope was granted."""
        return scope in self.granted_scopes

    def has_all_scopes(self, scopes: list[str]) -> bool:
        """Check if all required scopes were granted."""
        return all(s in self.granted_scopes for s in scopes)
```

### Step 4: Validate Scopes in Services

`app/integrations/google/service.py`:

```python
from app.oauth.scopes import GoogleScope

class GooglePhotosService:
    REQUIRED_SCOPES = [
        GoogleScope.PHOTOS_READONLY.value,
    ]

    def __init__(self, token: OAuthToken):
        self._token = token
        self._validate_scopes()

    def _validate_scopes(self):
        """Ensure token has required scopes."""
        if not self._token.has_all_scopes(self.REQUIRED_SCOPES):
            missing = [s for s in self.REQUIRED_SCOPES if not self._token.has_scope(s)]
            raise InsufficientScopesError(
                f"Missing required scopes: {missing}. "
                "Please reconnect with the 'photos' scope set."
            )
```

### Step 5: Add Scope Info Endpoint

```python
@router.get("/scopes/{provider}")
async def list_scope_sets(provider: ValidProvider):
    """List available scope sets for a provider."""
    from app.oauth.scopes import GOOGLE_SCOPE_SETS, ADOBE_SCOPE_SETS

    sets = {
        "google": GOOGLE_SCOPE_SETS,
        "adobe": ADOBE_SCOPE_SETS,
    }.get(provider, {})

    return {
        "provider": provider,
        "scope_sets": [
            {
                "name": s.name,
                "description": s.description,
                "scopes": s.scopes,
            }
            for s in sets.values()
        ],
    }
```

## Testing

```python
class TestOAuthScopes:
    def test_get_google_photos_scopes(self):
        scope_set = get_scope_set("google", "photos")
        assert "photoslibrary" in " ".join(scope_set.scopes)

    def test_unknown_scope_set_raises(self):
        with pytest.raises(ValueError):
            get_scope_set("google", "nonexistent")

    def test_token_has_scope(self):
        token = OAuthToken(
            provider="google",
            access_token="test",
            granted_scopes=["openid", "email"],
        )
        assert token.has_scope("email")
        assert not token.has_scope("photos")
```

## Success Criteria

1. Can request different scope sets via query param
2. Scopes stored with token
3. Services validate required scopes
4. Clear error when scopes insufficient
5. Endpoint to list available scope sets

## API Changes

| Endpoint | Change |
|----------|--------|
| `GET /oauth/{provider}/connect` | Add `?scopes=` query param |
| `GET /oauth/scopes/{provider}` | NEW: List scope sets |
