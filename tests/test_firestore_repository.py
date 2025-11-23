"""
Tests for FirestoreUserRepository and encryption utilities.

These tests use mocking for unit testing and can be run with the Firestore emulator
for integration testing.
"""

import os
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.users.models import User


# Generate a valid Fernet key for testing
TEST_ENCRYPTION_KEY = "3xpo7t61pLEqmOiHEZs4qIvrPjieKmO1Pg5OSdwDRAI="


class TestEncryption:
    """Tests for encryption utilities."""

    @pytest.fixture(autouse=True)
    def reset_encryption(self):
        """Reset encryption singleton before each test."""
        from app.infrastructure.encryption import reset_encryption

        reset_encryption()
        yield
        reset_encryption()

    def test_encrypt_token_without_key_raises(self):
        """Test that encryption fails without TOKEN_ENCRYPTION_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove TOKEN_ENCRYPTION_KEY if present
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)

            from app.infrastructure.encryption import encrypt_token, reset_encryption

            reset_encryption()

            with pytest.raises(ValueError, match="TOKEN_ENCRYPTION_KEY"):
                encrypt_token("test-token")

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encryption and decryption work correctly."""
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            from app.infrastructure.encryption import (
                decrypt_token,
                encrypt_token,
                reset_encryption,
            )

            reset_encryption()

            original = "my-secret-access-token"
            encrypted = encrypt_token(original)

            # Encrypted should be different from original
            assert encrypted != original

            # Decrypted should match original
            decrypted = decrypt_token(encrypted)
            assert decrypted == original

    def test_encrypt_optional_none(self):
        """Test that encrypt_token_optional handles None."""
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            from app.infrastructure.encryption import (
                encrypt_token_optional,
                reset_encryption,
            )

            reset_encryption()

            result = encrypt_token_optional(None)
            assert result is None

    def test_decrypt_optional_none(self):
        """Test that decrypt_token_optional handles None."""
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            from app.infrastructure.encryption import (
                decrypt_token_optional,
                reset_encryption,
            )

            reset_encryption()

            result = decrypt_token_optional(None)
            assert result is None

    def test_generate_encryption_key(self):
        """Test encryption key generation."""
        from app.infrastructure.encryption import generate_encryption_key

        key = generate_encryption_key()

        # Key should be a non-empty string
        assert isinstance(key, str)
        assert len(key) > 0

        # Key should be valid for Fernet
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": key}):
            from app.infrastructure.encryption import (
                decrypt_token,
                encrypt_token,
                reset_encryption,
            )

            reset_encryption()

            encrypted = encrypt_token("test")
            decrypted = decrypt_token(encrypted)
            assert decrypted == "test"

    def test_is_encryption_configured(self):
        """Test checking if encryption is configured."""
        from app.infrastructure.encryption import is_encryption_configured

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
            assert is_encryption_configured() is False

        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            assert is_encryption_configured() is True

    def test_decrypt_invalid_token_raises(self):
        """Test that decrypting invalid data raises EncryptionError."""
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            from app.infrastructure.encryption import (
                EncryptionError,
                decrypt_token,
                reset_encryption,
            )

            reset_encryption()

            with pytest.raises(EncryptionError, match="Decryption failed"):
                decrypt_token("invalid-not-encrypted-data")


class TestFirestoreUserRepository:
    """Tests for FirestoreUserRepository."""

    @pytest.fixture(autouse=True)
    def setup_encryption(self):
        """Set up encryption for tests."""
        from app.infrastructure.encryption import reset_encryption

        reset_encryption()
        with patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": TEST_ENCRYPTION_KEY}):
            yield
        reset_encryption()

    @pytest.fixture
    def mock_db(self):
        """Create a mock Firestore client."""
        db = MagicMock()
        return db

    @pytest.fixture
    def repository(self, mock_db):
        """Create repository with mock database."""
        from app.infrastructure.firestore_repository import FirestoreUserRepository

        return FirestoreUserRepository(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_uid_not_found(self, repository, mock_db):
        """Test getting non-existent user returns None."""
        # Setup mock
        mock_doc_ref = MagicMock()
        mock_doc = AsyncMock()
        mock_doc.exists = False
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = await repository.get_by_uid("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_uid_found(self, repository, mock_db):
        """Test getting existing user."""
        # Setup mock user document
        mock_doc_ref = MagicMock()
        mock_doc = MagicMock()  # Use MagicMock for sync methods
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "uid": "uid-123",
            "email": "test@example.com",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)

        # Setup mock tokens subcollection (empty)
        mock_tokens_ref = MagicMock()

        async def empty_stream():
            return
            yield  # Make it an async generator

        mock_tokens_ref.stream.return_value = empty_stream()

        mock_doc_ref.collection.return_value = mock_tokens_ref
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = await repository.get_by_uid("uid-123")

        assert result is not None
        assert result.uid == "uid-123"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user(self, repository, mock_db):
        """Test creating a new user."""
        user = User(uid="uid-123", email="test@example.com")

        # Setup mock - user doesn't exist
        mock_doc_ref = MagicMock()
        mock_doc = AsyncMock()
        mock_doc.exists = False
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_doc_ref.set = AsyncMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = await repository.create(user)

        assert result.uid == "uid-123"
        assert result.email == "test@example.com"
        mock_doc_ref.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_raises(self, repository, mock_db):
        """Test creating duplicate user raises ValueError."""
        user = User(uid="uid-123", email="test@example.com")

        # Setup mock - user exists
        mock_doc_ref = MagicMock()
        mock_doc = AsyncMock()
        mock_doc.exists = True
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        with pytest.raises(ValueError, match="already exists"):
            await repository.create(user)

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, repository, mock_db):
        """Test get_or_create creates new user when not exists."""
        # Setup mock - user doesn't exist
        mock_doc_ref = MagicMock()
        mock_doc = AsyncMock()
        mock_doc.exists = False
        mock_doc.to_dict.return_value = None
        mock_doc_ref.get = AsyncMock(return_value=mock_doc)
        mock_doc_ref.set = AsyncMock()

        # For tokens subcollection
        mock_tokens_ref = MagicMock()

        async def empty_stream():
            return
            yield

        mock_tokens_ref.stream.return_value = empty_stream()
        mock_doc_ref.collection.return_value = mock_tokens_ref

        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = await repository.get_or_create("uid-123", "test@example.com")

        assert result.uid == "uid-123"
        assert result.email == "test@example.com"
        mock_doc_ref.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_token(self, repository, mock_db):
        """Test saving token for user."""
        # Setup mock - user exists
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = True
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)
        mock_user_doc.update = AsyncMock()

        # Setup mock token doc
        mock_token_doc = MagicMock()
        mock_token_doc.set = AsyncMock()

        mock_tokens_collection = MagicMock()
        mock_tokens_collection.document.return_value = mock_token_doc
        mock_user_doc.collection.return_value = mock_tokens_collection

        mock_db.collection.return_value.document.return_value = mock_user_doc

        token_data = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_at": 1700000000,
        }

        result = await repository.save_token("uid-123", "google", token_data)

        assert result.provider == "google"
        assert result.access_token == "test-access-token"
        mock_token_doc.set.assert_called_once()
        mock_user_doc.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_exists(self, repository, mock_db):
        """Test getting token that exists."""
        from app.infrastructure.encryption import encrypt_token

        # Encrypt the tokens as they would be stored
        encrypted_access = encrypt_token("test-access-token")
        encrypted_refresh = encrypt_token("test-refresh-token")

        # Setup mock
        mock_token_doc = MagicMock()
        mock_token_snapshot = MagicMock()  # Use MagicMock for sync methods
        mock_token_snapshot.exists = True
        mock_token_snapshot.to_dict.return_value = {
            "provider": "google",
            "access_token": encrypted_access,
            "refresh_token": encrypted_refresh,
            "expires_at": 1700000000,
            "token_type": "Bearer",
            "scope": "email profile",
            "connected_at": datetime.now(UTC),
        }
        mock_token_doc.get = AsyncMock(return_value=mock_token_snapshot)

        mock_tokens_collection = MagicMock()
        mock_tokens_collection.document.return_value = mock_token_doc

        mock_user_doc = MagicMock()
        mock_user_doc.collection.return_value = mock_tokens_collection

        mock_db.collection.return_value.document.return_value = mock_user_doc

        result = await repository.get_token("uid-123", "google")

        assert result is not None
        assert result.provider == "google"
        assert result.access_token == "test-access-token"
        assert result.refresh_token == "test-refresh-token"

    @pytest.mark.asyncio
    async def test_get_token_not_found(self, repository, mock_db):
        """Test getting token that doesn't exist."""
        # Setup mock
        mock_token_doc = MagicMock()
        mock_token_snapshot = AsyncMock()
        mock_token_snapshot.exists = False
        mock_token_doc.get = AsyncMock(return_value=mock_token_snapshot)

        mock_tokens_collection = MagicMock()
        mock_tokens_collection.document.return_value = mock_token_doc

        mock_user_doc = MagicMock()
        mock_user_doc.collection.return_value = mock_tokens_collection

        mock_db.collection.return_value.document.return_value = mock_user_doc

        result = await repository.get_token("uid-123", "google")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_token_success(self, repository, mock_db):
        """Test deleting existing token."""
        # Setup mock - user exists
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = True
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)
        mock_user_doc.update = AsyncMock()

        # Setup mock - token exists
        mock_token_doc = MagicMock()
        mock_token_snapshot = AsyncMock()
        mock_token_snapshot.exists = True
        mock_token_doc.get = AsyncMock(return_value=mock_token_snapshot)
        mock_token_doc.delete = AsyncMock()

        mock_tokens_collection = MagicMock()
        mock_tokens_collection.document.return_value = mock_token_doc
        mock_user_doc.collection.return_value = mock_tokens_collection

        mock_db.collection.return_value.document.return_value = mock_user_doc

        result = await repository.delete_token("uid-123", "google")

        assert result is True
        mock_token_doc.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_token_user_not_found(self, repository, mock_db):
        """Test deleting token for non-existent user."""
        # Setup mock - user doesn't exist
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = False
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)

        mock_db.collection.return_value.document.return_value = mock_user_doc

        result = await repository.delete_token("non-existent", "google")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_token_provider_not_found(self, repository, mock_db):
        """Test deleting token for non-connected provider."""
        # Setup mock - user exists but token doesn't
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = True
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)

        mock_token_doc = MagicMock()
        mock_token_snapshot = AsyncMock()
        mock_token_snapshot.exists = False
        mock_token_doc.get = AsyncMock(return_value=mock_token_snapshot)

        mock_tokens_collection = MagicMock()
        mock_tokens_collection.document.return_value = mock_token_doc
        mock_user_doc.collection.return_value = mock_tokens_collection

        mock_db.collection.return_value.document.return_value = mock_user_doc

        result = await repository.delete_token("uid-123", "google")

        assert result is False

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, repository, mock_db):
        """Test listing connections for user with none."""
        # Setup mock - user exists
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = True
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)

        # Empty tokens subcollection
        mock_tokens_ref = MagicMock()

        async def empty_stream():
            return
            yield

        mock_tokens_ref.stream.return_value = empty_stream()
        mock_user_doc.collection.return_value = mock_tokens_ref

        mock_db.collection.return_value.document.return_value = mock_user_doc

        connections = await repository.list_connections("uid-123")

        assert connections == []

    @pytest.mark.asyncio
    async def test_list_connections_multiple(self, repository, mock_db):
        """Test listing multiple connections."""
        # Setup mock - user exists
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = True
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)

        # Mock token documents
        mock_google_doc = MagicMock()
        mock_google_doc.id = "google"

        mock_adobe_doc = MagicMock()
        mock_adobe_doc.id = "adobe"

        mock_tokens_ref = MagicMock()

        async def token_stream():
            yield mock_google_doc
            yield mock_adobe_doc

        mock_tokens_ref.stream.return_value = token_stream()
        mock_user_doc.collection.return_value = mock_tokens_ref

        mock_db.collection.return_value.document.return_value = mock_user_doc

        connections = await repository.list_connections("uid-123")

        assert set(connections) == {"google", "adobe"}

    @pytest.mark.asyncio
    async def test_list_connections_user_not_found(self, repository, mock_db):
        """Test listing connections for non-existent user."""
        # Setup mock - user doesn't exist
        mock_user_doc = MagicMock()
        mock_user_snapshot = AsyncMock()
        mock_user_snapshot.exists = False
        mock_user_doc.get = AsyncMock(return_value=mock_user_snapshot)

        mock_db.collection.return_value.document.return_value = mock_user_doc

        connections = await repository.list_connections("non-existent")

        assert connections == []


class TestFirestoreClient:
    """Tests for Firestore client utilities."""

    @pytest.fixture(autouse=True)
    def reset_client(self):
        """Reset Firestore client singleton before each test."""
        from app.infrastructure.firestore import reset_firestore_client

        reset_firestore_client()
        yield
        reset_firestore_client()

    def test_is_firestore_available_without_project(self):
        """Test that Firestore is not available without project ID."""
        from app.infrastructure.firestore import is_firestore_available

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GCP_PROJECT_ID", None)
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            assert is_firestore_available() is False

    def test_is_firestore_available_with_project(self):
        """Test that Firestore is available with project ID."""
        from app.infrastructure.firestore import is_firestore_available

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}):
            assert is_firestore_available() is True

    def test_get_firestore_client_without_project_raises(self):
        """Test that getting client without project raises ValueError."""
        from app.infrastructure.firestore import (
            get_firestore_client,
            reset_firestore_client,
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GCP_PROJECT_ID", None)
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            reset_firestore_client()

            with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
                get_firestore_client()


class TestRepositoryFactory:
    """Tests for repository factory functions."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset all singletons before each test."""
        from app.infrastructure.encryption import reset_encryption
        from app.infrastructure.firestore import reset_firestore_client
        from app.users.repository import reset_user_repository

        reset_user_repository()
        reset_firestore_client()
        reset_encryption()
        yield
        reset_user_repository()
        reset_firestore_client()
        reset_encryption()

    def test_get_user_repository_returns_in_memory_without_config(self):
        """Test that InMemoryUserRepository is returned without Firestore config."""
        from app.users.repository import (
            InMemoryUserRepository,
            get_user_repository,
            reset_user_repository,
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GCP_PROJECT_ID", None)
            os.environ.pop("GOOGLE_CLOUD_PROJECT", None)
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
            reset_user_repository()

            repo = get_user_repository()

            assert isinstance(repo, InMemoryUserRepository)

    def test_get_user_repository_requires_encryption_key(self):
        """Test that InMemoryUserRepository is returned without encryption key."""
        from app.users.repository import (
            InMemoryUserRepository,
            get_user_repository,
            reset_user_repository,
        )

        # Only project ID, no encryption key
        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}, clear=True):
            os.environ.pop("TOKEN_ENCRYPTION_KEY", None)
            reset_user_repository()

            repo = get_user_repository()

            # Should fall back to in-memory without encryption key
            assert isinstance(repo, InMemoryUserRepository)
