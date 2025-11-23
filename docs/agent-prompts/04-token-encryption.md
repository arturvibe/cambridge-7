# Agent Task: Implement Token Encryption

## Context

You are working on a FastAPI application that stores OAuth2 tokens for external services (Google, Adobe). Currently, tokens are stored in plaintext. Your task is to implement encryption at rest for sensitive token fields.

## Security Requirement

OAuth access tokens and refresh tokens must be encrypted before storage and decrypted when retrieved. This protects tokens if the database is compromised.

## Architecture Overview

```
OAuthToken (plaintext in memory)
        ↓
    TokenEncryption.encrypt()
        ↓
Repository stores encrypted tokens
        ↓
    TokenEncryption.decrypt()
        ↓
OAuthToken (plaintext for API calls)
```

## Your Task

1. Create `app/infrastructure/encryption.py` with `TokenEncryption` class
2. Integrate encryption into `UserRepository` implementations
3. Handle key rotation (future-proofing)

## Files to Read First

1. `app/users/models.py` - OAuthToken model (fields to encrypt)
2. `app/users/repository.py` - Where encryption is applied
3. `AGENTS.md` - Project conventions

## Implementation

### Step 1: Create Encryption Module

`app/infrastructure/encryption.py`:

```python
"""
Token encryption for OAuth credentials at rest.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC).
Key is loaded from TOKEN_ENCRYPTION_KEY environment variable.
"""

import os
import logging
from functools import lru_cache
from base64 import urlsafe_b64encode, urlsafe_b64decode

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class TokenEncryption:
    """
    Encrypts and decrypts OAuth tokens using Fernet (symmetric encryption).

    The encryption key is derived from TOKEN_ENCRYPTION_KEY env var.
    If no key is set, a warning is logged and encryption is disabled (dev only).
    """

    def __init__(self, key: str | None = None):
        """
        Initialize encryption with key.

        Args:
            key: Base64-encoded 32-byte key, or None to load from env
        """
        self._key = key or os.getenv("TOKEN_ENCRYPTION_KEY")
        self._fernet: Fernet | None = None
        self._enabled = True

        if not self._key:
            logger.warning(
                "TOKEN_ENCRYPTION_KEY not set - token encryption DISABLED. "
                "This is only acceptable in development."
            )
            self._enabled = False
        else:
            self._fernet = self._create_fernet(self._key)

    def _create_fernet(self, key: str) -> Fernet:
        """Create Fernet instance from key string."""
        try:
            # If key is already valid Fernet key (32 bytes, base64)
            return Fernet(key.encode() if isinstance(key, str) else key)
        except Exception:
            # Derive key from passphrase using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"cambridge-oauth-tokens",  # Static salt is OK for this use case
                iterations=100_000,
            )
            derived_key = urlsafe_b64encode(kdf.derive(key.encode()))
            return Fernet(derived_key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string value.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            EncryptionError: If encryption fails
        """
        if not self._enabled:
            return plaintext

        if not plaintext:
            return plaintext

        try:
            encrypted = self._fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError(f"Failed to encrypt token: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionError: If decryption fails (wrong key, corrupted data)
        """
        if not self._enabled:
            return ciphertext

        if not ciphertext:
            return ciphertext

        try:
            decrypted = self._fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed - invalid token (wrong key?)")
            raise EncryptionError(
                "Failed to decrypt token - encryption key may have changed"
            )
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise EncryptionError(f"Failed to decrypt token: {e}")

    @property
    def is_enabled(self) -> bool:
        """Check if encryption is enabled."""
        return self._enabled


@lru_cache()
def get_token_encryption() -> TokenEncryption:
    """Get singleton TokenEncryption instance."""
    return TokenEncryption()


def generate_encryption_key() -> str:
    """
    Generate a new random encryption key.

    Use this to create a new TOKEN_ENCRYPTION_KEY value.

    Returns:
        Base64-encoded 32-byte key suitable for Fernet
    """
    return Fernet.generate_key().decode()
```

### Step 2: Create Encrypted Token Model

`app/users/encrypted_models.py`:

```python
"""
Encrypted versions of token models for storage.
"""

from app.users.models import OAuthToken
from app.infrastructure.encryption import get_token_encryption


class EncryptedOAuthToken:
    """Helper for encrypting/decrypting OAuthToken fields."""

    # Fields that should be encrypted
    ENCRYPTED_FIELDS = {"access_token", "refresh_token"}

    @classmethod
    def encrypt(cls, token: OAuthToken) -> dict:
        """
        Encrypt sensitive fields for storage.

        Returns dict suitable for database storage.
        """
        encryption = get_token_encryption()
        data = token.model_dump()

        for field in cls.ENCRYPTED_FIELDS:
            if data.get(field):
                data[field] = encryption.encrypt(data[field])

        return data

    @classmethod
    def decrypt(cls, data: dict) -> OAuthToken:
        """
        Decrypt sensitive fields and return OAuthToken.

        Args:
            data: Dict from database with encrypted fields

        Returns:
            OAuthToken with decrypted values
        """
        encryption = get_token_encryption()
        decrypted_data = data.copy()

        for field in cls.ENCRYPTED_FIELDS:
            if decrypted_data.get(field):
                decrypted_data[field] = encryption.decrypt(decrypted_data[field])

        return OAuthToken(**decrypted_data)
```

### Step 3: Update InMemoryUserRepository

Update `app/users/repository.py` to use encryption:

```python
from app.infrastructure.encryption import get_token_encryption

class InMemoryUserRepository(UserRepository):
    """In-memory implementation with token encryption."""

    async def save_token(
        self, uid: str, provider: str, token_data: dict[str, Any]
    ) -> OAuthToken:
        encryption = get_token_encryption()

        # Create token from OAuth response
        token = OAuthToken.from_oauth_response(provider, token_data)

        # Encrypt before storing
        encrypted_token = OAuthToken(
            provider=token.provider,
            access_token=encryption.encrypt(token.access_token),
            refresh_token=encryption.encrypt(token.refresh_token) if token.refresh_token else None,
            expires_at=token.expires_at,
            token_type=token.token_type,
            scope=token.scope,
            connected_at=token.connected_at,
        )

        user.tokens[provider] = encrypted_token
        # ... rest of method

        return token  # Return unencrypted for immediate use

    async def get_token(self, uid: str, provider: str) -> OAuthToken | None:
        user = self._users.get(uid)
        if not user:
            return None

        encrypted_token = user.tokens.get(provider)
        if not encrypted_token:
            return None

        # Decrypt before returning
        encryption = get_token_encryption()
        return OAuthToken(
            provider=encrypted_token.provider,
            access_token=encryption.decrypt(encrypted_token.access_token),
            refresh_token=encryption.decrypt(encrypted_token.refresh_token) if encrypted_token.refresh_token else None,
            expires_at=encrypted_token.expires_at,
            token_type=encrypted_token.token_type,
            scope=encrypted_token.scope,
            connected_at=encrypted_token.connected_at,
        )
```

### Step 4: Add CLI Tool for Key Generation

`scripts/generate-encryption-key.py`:

```python
#!/usr/bin/env python3
"""Generate a new encryption key for TOKEN_ENCRYPTION_KEY."""

from app.infrastructure.encryption import generate_encryption_key

if __name__ == "__main__":
    key = generate_encryption_key()
    print(f"Generated encryption key:\n\n{key}\n")
    print("Add to your environment:")
    print(f'export TOKEN_ENCRYPTION_KEY="{key}"')
```

## Environment Variables

```bash
# Required in production
TOKEN_ENCRYPTION_KEY=your-base64-encoded-32-byte-key

# Generate with:
python scripts/generate-encryption-key.py
```

## Testing Requirements

Create `tests/infrastructure/test_encryption.py`:

```python
import pytest
from app.infrastructure.encryption import (
    TokenEncryption,
    EncryptionError,
    generate_encryption_key,
)

class TestTokenEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        key = generate_encryption_key()
        encryption = TokenEncryption(key)

        plaintext = "secret-access-token-12345"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)

        assert encrypted != plaintext  # Actually encrypted
        assert decrypted == plaintext  # Correctly decrypted

    def test_encrypt_empty_string(self):
        key = generate_encryption_key()
        encryption = TokenEncryption(key)

        assert encryption.encrypt("") == ""
        assert encryption.decrypt("") == ""

    def test_decrypt_with_wrong_key_fails(self):
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        encryption1 = TokenEncryption(key1)
        encryption2 = TokenEncryption(key2)

        encrypted = encryption1.encrypt("secret")

        with pytest.raises(EncryptionError):
            encryption2.decrypt(encrypted)

    def test_disabled_without_key(self, monkeypatch):
        monkeypatch.delenv("TOKEN_ENCRYPTION_KEY", raising=False)

        encryption = TokenEncryption(key=None)

        assert not encryption.is_enabled
        assert encryption.encrypt("secret") == "secret"  # Passthrough
        assert encryption.decrypt("secret") == "secret"

    def test_generate_key_format(self):
        key = generate_encryption_key()

        assert len(key) == 44  # Base64 of 32 bytes
        assert key.endswith("=")  # Base64 padding
```

## Key Rotation Strategy

For future key rotation:

```python
class TokenEncryption:
    def __init__(self, current_key: str, previous_keys: list[str] | None = None):
        self._current = Fernet(current_key)
        self._previous = [Fernet(k) for k in (previous_keys or [])]

    def decrypt(self, ciphertext: str) -> str:
        # Try current key first
        try:
            return self._current.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            pass

        # Try previous keys
        for fernet in self._previous:
            try:
                return fernet.decrypt(ciphertext.encode()).decode()
            except InvalidToken:
                continue

        raise EncryptionError("Failed to decrypt with any known key")
```

## Dependencies to Add

```
cryptography==42.0.0
```

## Success Criteria

1. Tokens encrypted before storage
2. Tokens decrypted correctly when retrieved
3. Works with/without encryption key (dev vs prod)
4. Key generation script works
5. Tests pass
6. No plaintext tokens in storage

## Do NOT

- Use hardcoded encryption keys
- Store keys in code
- Use weak encryption algorithms
- Break existing token flow
- Make encryption blocking/slow
