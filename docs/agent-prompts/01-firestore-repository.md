# Agent Task: Implement Firestore User Repository

## Context

You are working on a FastAPI application that uses Magic Link authentication (Firebase) as the primary identity source. Users can connect external OAuth2 services (Google, Adobe). The OAuth2 foundation is complete with an in-memory repository - your task is to implement persistent storage using Firestore.

## Architecture Overview

```
Magic Link Auth → Firebase UID (primary key)
                      ↓
              UserRepository (interface)
                      ↓
         InMemoryUserRepository (current - temporary)
         FirestoreUserRepository (your task - persistent)
```

## Your Task

Implement `FirestoreUserRepository` in `app/infrastructure/firestore_repository.py` that:
1. Implements the `UserRepository` interface from `app/users/repository.py`
2. Stores users and OAuth tokens in Firestore
3. Encrypts OAuth tokens at rest (access_token, refresh_token)

## Files to Read First

1. `app/users/repository.py` - The interface you must implement
2. `app/users/models.py` - User and OAuthToken models
3. `app/oauth/router.py` - How the repository is used
4. `AGENTS.md` - Project conventions

## Interface to Implement

```python
class UserRepository(Protocol):
    async def get_by_uid(self, uid: str) -> User | None
    async def create(self, user: User) -> User
    async def get_or_create(self, uid: str, email: str) -> User
    async def save_token(self, uid: str, provider: str, token_data: dict) -> OAuthToken
    async def get_token(self, uid: str, provider: str) -> OAuthToken | None
    async def delete_token(self, uid: str, provider: str) -> bool
    async def list_connections(self, uid: str) -> list[str]
```

Note: Uses `Protocol` (structural subtyping) not `ABC` - no explicit inheritance required.

## Firestore Data Model

```
Collection: users
Document ID: {firebase_uid}
Fields:
  - uid: string
  - email: string
  - created_at: timestamp
  - updated_at: timestamp

Subcollection: users/{uid}/tokens
Document ID: {provider}  (e.g., "google", "adobe")
Fields:
  - provider: string
  - access_token: string (encrypted)
  - refresh_token: string (encrypted, nullable)
  - expires_at: number (nullable)
  - token_type: string
  - scope: string (nullable)
  - connected_at: timestamp
```

## Implementation Requirements

### 1. Create Firestore Client (`app/infrastructure/firestore.py`)

```python
# Auto-detect emulator via FIRESTORE_EMULATOR_HOST
# Use Application Default Credentials in production
```

### 2. Create FirestoreUserRepository (`app/infrastructure/firestore_repository.py`)

```python
from google.cloud import firestore
from app.users.repository import UserRepository
from app.users.models import User, OAuthToken

class FirestoreUserRepository(UserRepository):
    def __init__(self, db: firestore.AsyncClient):
        self._db = db
        self._users = db.collection("users")

    # Implement all interface methods...
```

### 3. Token Encryption

Create `app/infrastructure/encryption.py`:
- Use `cryptography.fernet` for symmetric encryption
- Key from `TOKEN_ENCRYPTION_KEY` environment variable
- Encrypt: access_token, refresh_token before storing
- Decrypt: when retrieving tokens

### 4. Wire Into Application

Update `app/users/repository.py`:
```python
def get_user_repository() -> UserRepository:
    # Return FirestoreUserRepository if Firestore available
    # Fall back to InMemoryUserRepository for tests
```

## Environment Variables

```
FIRESTORE_EMULATOR_HOST=localhost:8080  # Local dev
TOKEN_ENCRYPTION_KEY=your-32-byte-base64-key  # Required
```

## Testing Requirements

Create `tests/test_firestore_repository.py`:
1. Test with Firestore emulator
2. Test all CRUD operations
3. Test token encryption/decryption
4. Test error handling (user not found, etc.)

## Update docker-compose.yml

Add Firestore emulator:
```yaml
firestore-emulator:
  image: gcr.io/google.com/cloudsdktool/cloud-sdk:emulators
  command: gcloud emulators firestore start --host-port=0.0.0.0:8080
  ports:
    - "8080:8080"
```

## Dependencies to Add

```
google-cloud-firestore==2.14.0
cryptography==42.0.0
```

## Success Criteria

1. All `UserRepository` interface methods implemented
2. Tokens encrypted at rest
3. Works with Firestore emulator locally
4. Tests pass with 90%+ coverage
5. Existing OAuth flow works with new repository

## Do NOT

- Change the UserRepository interface
- Modify OAuth router logic
- Store tokens in plaintext
- Break existing tests
