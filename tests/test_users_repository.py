"""
Tests for UserRepository implementations.
"""

import pytest

from app.users.models import OAuthToken, User
from app.users.repository import (
    InMemoryUserRepository,
    get_user_repository,
    set_user_repository,
)


class TestInMemoryUserRepository:
    """Tests for InMemoryUserRepository."""

    @pytest.fixture
    def repository(self):
        """Create fresh repository for each test."""
        return InMemoryUserRepository()

    @pytest.mark.asyncio
    async def test_get_by_uid_not_found(self, repository):
        """Test getting non-existent user returns None."""
        result = await repository.get_by_uid("non-existent")
        assert result is None

    @pytest.mark.asyncio
    async def test_create_user(self, repository):
        """Test creating a new user."""
        user = User(uid="uid-123", email="test@example.com")

        created = await repository.create(user)

        assert created.uid == "uid-123"
        assert created.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_raises(self, repository):
        """Test creating duplicate user raises ValueError."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        with pytest.raises(ValueError, match="already exists"):
            await repository.create(user)

    @pytest.mark.asyncio
    async def test_get_by_uid_after_create(self, repository):
        """Test getting user after creation."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        result = await repository.get_by_uid("uid-123")

        assert result is not None
        assert result.uid == "uid-123"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self, repository):
        """Test get_or_create creates new user when not exists."""
        result = await repository.get_or_create("uid-123", "test@example.com")

        assert result.uid == "uid-123"
        assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self, repository):
        """Test get_or_create returns existing user."""
        user = User(uid="uid-123", email="original@example.com")
        await repository.create(user)

        result = await repository.get_or_create("uid-123", "different@example.com")

        assert result.uid == "uid-123"
        assert result.email == "original@example.com"  # Original email preserved

    @pytest.mark.asyncio
    async def test_save_token_for_existing_user(self, repository):
        """Test saving token for existing user."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        token_data = {
            "access_token": "test-access-token",
            "refresh_token": "test-refresh-token",
            "expires_at": 1700000000,
        }

        result = await repository.save_token("uid-123", "google", token_data)

        assert result.provider == "google"
        assert result.access_token == "test-access-token"
        assert result.refresh_token == "test-refresh-token"

    @pytest.mark.asyncio
    async def test_save_token_creates_placeholder_user(self, repository):
        """Test saving token creates placeholder user if not exists."""
        token_data = {"access_token": "test-token"}

        result = await repository.save_token("uid-123", "google", token_data)

        assert result.access_token == "test-token"
        user = await repository.get_by_uid("uid-123")
        assert user is not None

    @pytest.mark.asyncio
    async def test_save_token_updates_existing_provider(self, repository):
        """Test saving token updates existing provider token."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        await repository.save_token("uid-123", "google", {"access_token": "first"})
        await repository.save_token("uid-123", "google", {"access_token": "second"})

        token = await repository.get_token("uid-123", "google")
        assert token is not None
        assert token.access_token == "second"

    @pytest.mark.asyncio
    async def test_get_token_exists(self, repository):
        """Test getting token that exists."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)
        await repository.save_token("uid-123", "google", {"access_token": "test"})

        token = await repository.get_token("uid-123", "google")

        assert token is not None
        assert token.access_token == "test"

    @pytest.mark.asyncio
    async def test_get_token_user_not_found(self, repository):
        """Test getting token for non-existent user."""
        token = await repository.get_token("non-existent", "google")
        assert token is None

    @pytest.mark.asyncio
    async def test_get_token_provider_not_found(self, repository):
        """Test getting token for non-connected provider."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        token = await repository.get_token("uid-123", "google")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token_success(self, repository):
        """Test deleting existing token."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)
        await repository.save_token("uid-123", "google", {"access_token": "test"})

        result = await repository.delete_token("uid-123", "google")

        assert result is True
        token = await repository.get_token("uid-123", "google")
        assert token is None

    @pytest.mark.asyncio
    async def test_delete_token_user_not_found(self, repository):
        """Test deleting token for non-existent user."""
        result = await repository.delete_token("non-existent", "google")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_token_provider_not_found(self, repository):
        """Test deleting token for non-connected provider."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        result = await repository.delete_token("uid-123", "google")
        assert result is False

    @pytest.mark.asyncio
    async def test_list_connections_empty(self, repository):
        """Test listing connections for user with none."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)

        connections = await repository.list_connections("uid-123")
        assert connections == []

    @pytest.mark.asyncio
    async def test_list_connections_multiple(self, repository):
        """Test listing multiple connections."""
        user = User(uid="uid-123", email="test@example.com")
        await repository.create(user)
        await repository.save_token("uid-123", "google", {"access_token": "g"})
        await repository.save_token("uid-123", "adobe", {"access_token": "a"})

        connections = await repository.list_connections("uid-123")

        assert set(connections) == {"google", "adobe"}

    @pytest.mark.asyncio
    async def test_list_connections_user_not_found(self, repository):
        """Test listing connections for non-existent user."""
        connections = await repository.list_connections("non-existent")
        assert connections == []


class TestRepositorySingleton:
    """Tests for repository singleton management."""

    def test_get_user_repository_returns_instance(self):
        """Test get_user_repository returns a repository."""
        repo = get_user_repository()
        assert repo is not None

    def test_set_user_repository_changes_instance(self):
        """Test set_user_repository changes the singleton."""
        original = get_user_repository()
        new_repo = InMemoryUserRepository()

        set_user_repository(new_repo)
        current = get_user_repository()

        assert current is new_repo
        assert current is not original

        # Reset for other tests
        set_user_repository(original)
