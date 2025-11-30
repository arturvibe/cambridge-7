"""
End-to-end tests for Firestore user repository.

These tests require the Firestore emulator to be running.
Run with: docker-compose up -d firebase-emulator firestore-emulator
"""

import pytest


@pytest.fixture
async def firestore_repository():
    """Create a fresh Firestore repository for each test."""
    # Reset singletons to ensure clean state
    from app.infrastructure.encryption import reset_encryption
    from app.infrastructure.firestore import reset_firestore_client

    reset_firestore_client()
    reset_encryption()

    from app.infrastructure.firestore import get_firestore_client
    from app.infrastructure.firestore_repository import FirestoreUserRepository

    client = get_firestore_client()
    repo = FirestoreUserRepository(client)

    yield repo

    # Cleanup: delete all test data
    await _cleanup_test_data(client)

    reset_firestore_client()
    reset_encryption()


async def _cleanup_test_data(client):
    """Delete all documents in the users collection."""
    users_ref = client.collection("users")
    async for doc in users_ref.stream():
        # Delete tokens subcollection first
        tokens_ref = doc.reference.collection("tokens")
        async for token_doc in tokens_ref.stream():
            await token_doc.reference.delete()
        # Then delete the user document
        await doc.reference.delete()


class TestFirestoreRepositoryE2E:
    """E2E tests for FirestoreUserRepository against actual Firestore emulator."""

    @pytest.mark.asyncio
    async def test_create_and_get_user(self, firestore_repository):
        """Test creating and retrieving a user."""
        from app.users.models import User

        # Create user
        user = User(uid="e2e-test-user-1", email="e2e-test@example.com")
        created = await firestore_repository.create(user)

        assert created.uid == "e2e-test-user-1"
        assert created.email == "e2e-test@example.com"

        # Retrieve user
        retrieved = await firestore_repository.get_by_uid("e2e-test-user-1")

        assert retrieved is not None
        assert retrieved.uid == "e2e-test-user-1"
        assert retrieved.email == "e2e-test@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, firestore_repository):
        """Test getting a user that doesn't exist."""
        result = await firestore_repository.get_by_uid("nonexistent-user")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_duplicate_user_raises(self, firestore_repository):
        """Test that creating a duplicate user raises ValueError."""
        from app.users.models import User

        user = User(uid="e2e-duplicate-user", email="duplicate@example.com")
        await firestore_repository.create(user)

        with pytest.raises(ValueError, match="already exists"):
            await firestore_repository.create(user)

    @pytest.mark.asyncio
    async def test_get_or_create_new_user(self, firestore_repository):
        """Test get_or_create creates a new user."""
        user = await firestore_repository.get_or_create(
            "e2e-new-user", "newuser@example.com"
        )

        assert user.uid == "e2e-new-user"
        assert user.email == "newuser@example.com"

        # Verify persisted
        retrieved = await firestore_repository.get_by_uid("e2e-new-user")
        assert retrieved is not None
        assert retrieved.email == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_existing_user(self, firestore_repository):
        """Test get_or_create returns existing user."""
        from app.users.models import User

        # Create user first
        original = User(uid="e2e-existing-user", email="original@example.com")
        await firestore_repository.create(original)

        # get_or_create should return existing user
        user = await firestore_repository.get_or_create(
            "e2e-existing-user", "different@example.com"
        )

        assert user.uid == "e2e-existing-user"
        assert user.email == "original@example.com"  # Original email preserved

    @pytest.mark.asyncio
    async def test_save_and_get_token(self, firestore_repository):
        """Test saving and retrieving OAuth tokens."""
        from app.users.models import User

        # Create user
        user = User(uid="e2e-token-user", email="token@example.com")
        await firestore_repository.create(user)

        # Save token
        token_data = {
            "access_token": "e2e-access-token-12345",
            "refresh_token": "e2e-refresh-token-67890",
            "expires_at": 1700000000,
            "token_type": "Bearer",
            "scope": "email profile",
        }
        saved_token = await firestore_repository.save_token(
            "e2e-token-user", "google", token_data
        )

        assert saved_token.provider == "google"
        assert saved_token.access_token == "e2e-access-token-12345"
        assert saved_token.refresh_token == "e2e-refresh-token-67890"

        # Retrieve token
        retrieved_token = await firestore_repository.get_token(
            "e2e-token-user", "google"
        )

        assert retrieved_token is not None
        assert retrieved_token.access_token == "e2e-access-token-12345"
        assert retrieved_token.refresh_token == "e2e-refresh-token-67890"
        assert retrieved_token.expires_at == 1700000000

    @pytest.mark.asyncio
    async def test_token_encryption_at_rest(self, firestore_repository):
        """Test that tokens are encrypted when stored in Firestore."""
        from app.users.models import User

        # Create user and save token
        user = User(uid="e2e-encryption-user", email="encryption@example.com")
        await firestore_repository.create(user)

        token_data = {
            "access_token": "plaintext-access-token",
            "refresh_token": "plaintext-refresh-token",
        }
        await firestore_repository.save_token(
            "e2e-encryption-user", "google", token_data
        )

        # Read raw data from Firestore to verify encryption
        from app.infrastructure.firestore import get_firestore_client

        client = get_firestore_client()
        token_doc = await (
            client.collection("users")
            .document("e2e-encryption-user")
            .collection("tokens")
            .document("google")
            .get()
        )

        raw_data = token_doc.to_dict()

        # Tokens should be encrypted (not plaintext)
        assert raw_data["access_token"] != "plaintext-access-token"
        assert raw_data["refresh_token"] != "plaintext-refresh-token"

        # But when retrieved through the repository, they should be decrypted
        retrieved = await firestore_repository.get_token(
            "e2e-encryption-user", "google"
        )
        assert retrieved.access_token == "plaintext-access-token"
        assert retrieved.refresh_token == "plaintext-refresh-token"

    @pytest.mark.asyncio
    async def test_get_token_nonexistent_user(self, firestore_repository):
        """Test getting token for nonexistent user returns None."""
        result = await firestore_repository.get_token("nonexistent", "google")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_token_nonexistent_provider(self, firestore_repository):
        """Test getting token for unconnected provider returns None."""
        from app.users.models import User

        user = User(uid="e2e-no-provider", email="noprovider@example.com")
        await firestore_repository.create(user)

        result = await firestore_repository.get_token("e2e-no-provider", "google")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_token(self, firestore_repository):
        """Test deleting a token."""
        from app.users.models import User

        # Create user and token
        user = User(uid="e2e-delete-token", email="delete@example.com")
        await firestore_repository.create(user)

        await firestore_repository.save_token(
            "e2e-delete-token", "google", {"access_token": "to-be-deleted"}
        )

        # Delete token
        result = await firestore_repository.delete_token("e2e-delete-token", "google")
        assert result is True

        # Verify deleted
        token = await firestore_repository.get_token("e2e-delete-token", "google")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token_nonexistent(self, firestore_repository):
        """Test deleting nonexistent token returns False."""
        from app.users.models import User

        user = User(uid="e2e-no-token-delete", email="nodelete@example.com")
        await firestore_repository.create(user)

        result = await firestore_repository.delete_token(
            "e2e-no-token-delete", "google"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, firestore_repository):
        """Test listing connections for user with none."""
        from app.users.models import User

        user = User(uid="e2e-no-connections", email="noconn@example.com")
        await firestore_repository.create(user)

        connections = await firestore_repository.list_connections("e2e-no-connections")
        assert connections == []

    @pytest.mark.asyncio
    async def test_list_connections_multiple(self, firestore_repository):
        """Test listing multiple connections."""
        from app.users.models import User

        user = User(uid="e2e-multi-connections", email="multi@example.com")
        await firestore_repository.create(user)

        # Add multiple providers
        await firestore_repository.save_token(
            "e2e-multi-connections", "google", {"access_token": "google-token"}
        )
        await firestore_repository.save_token(
            "e2e-multi-connections", "adobe", {"access_token": "adobe-token"}
        )

        connections = await firestore_repository.list_connections(
            "e2e-multi-connections"
        )
        assert set(connections) == {"google", "adobe"}

    @pytest.mark.asyncio
    async def test_update_existing_token(self, firestore_repository):
        """Test updating an existing token."""
        from app.users.models import User

        user = User(uid="e2e-update-token", email="update@example.com")
        await firestore_repository.create(user)

        # Save initial token
        await firestore_repository.save_token(
            "e2e-update-token", "google", {"access_token": "first-token"}
        )

        # Update token
        await firestore_repository.save_token(
            "e2e-update-token", "google", {"access_token": "second-token"}
        )

        # Verify updated
        token = await firestore_repository.get_token("e2e-update-token", "google")
        assert token.access_token == "second-token"

    @pytest.mark.asyncio
    async def test_user_with_tokens_loaded(self, firestore_repository):
        """Test that getting a user also loads their tokens."""
        from app.users.models import User

        # Create user with tokens
        user = User(uid="e2e-user-with-tokens", email="withtokens@example.com")
        await firestore_repository.create(user)

        await firestore_repository.save_token(
            "e2e-user-with-tokens", "google", {"access_token": "google-access"}
        )
        await firestore_repository.save_token(
            "e2e-user-with-tokens", "adobe", {"access_token": "adobe-access"}
        )

        # Get user - tokens should be loaded
        retrieved = await firestore_repository.get_by_uid("e2e-user-with-tokens")

        assert retrieved is not None
        assert len(retrieved.tokens) == 2
        assert "google" in retrieved.tokens
        assert "adobe" in retrieved.tokens
        assert retrieved.tokens["google"].access_token == "google-access"
        assert retrieved.tokens["adobe"].access_token == "adobe-access"
