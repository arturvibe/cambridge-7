"""
User repository interface and implementations.

Defines the port (interface) for user/token persistence.
Includes an in-memory implementation for testing and development.
Firestore implementation is available when configured.
"""

import logging
import os
from datetime import datetime, UTC
from typing import Any, Protocol

from app.users.models import OAuthToken, User


logger = logging.getLogger(__name__)


def _is_firestore_configured() -> bool:
    """Check if Firestore is configured via environment."""
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    encryption_key = os.getenv("TOKEN_ENCRYPTION_KEY")
    return project_id is not None and encryption_key is not None


class UserRepository(Protocol):
    """
    Protocol defining the user repository interface.

    This is the "port" in hexagonal architecture - it defines what
    operations the domain needs, without specifying how they're implemented.
    Uses Protocol for structural subtyping (duck typing), consistent with
    EventPublisher in app/core/ports.py.
    """

    async def get_by_uid(self, uid: str) -> User | None:
        """
        Get a user by Firebase UID.

        Args:
            uid: Firebase user ID

        Returns:
            User if found, None otherwise
        """
        ...

    async def create(self, user: User) -> User:
        """
        Create a new user.

        Args:
            user: User to create

        Returns:
            Created user

        Raises:
            ValueError: If user already exists
        """
        ...

    async def get_or_create(self, uid: str, email: str) -> User:
        """
        Get existing user or create new one.

        This is the primary method used after magic link authentication.

        Args:
            uid: Firebase user ID
            email: User's email address

        Returns:
            Existing or newly created user
        """
        ...

    async def save_token(
        self, uid: str, provider: str, token_data: dict[str, Any]
    ) -> OAuthToken:
        """
        Save OAuth token for a user.

        Creates the user if they don't exist (shouldn't happen in normal flow).

        Args:
            uid: Firebase user ID
            provider: OAuth provider name (google, adobe)
            token_data: Raw token dict from authlib

        Returns:
            Saved OAuthToken
        """
        ...

    async def get_token(self, uid: str, provider: str) -> OAuthToken | None:
        """
        Get OAuth token for a specific provider.

        Args:
            uid: Firebase user ID
            provider: OAuth provider name

        Returns:
            OAuthToken if found, None otherwise
        """
        ...

    async def delete_token(self, uid: str, provider: str) -> bool:
        """
        Delete OAuth token (disconnect service).

        Args:
            uid: Firebase user ID
            provider: OAuth provider name

        Returns:
            True if deleted, False if not found
        """
        ...

    async def list_connections(self, uid: str) -> list[str]:
        """
        List connected OAuth providers for a user.

        Args:
            uid: Firebase user ID

        Returns:
            List of provider names
        """
        ...


class InMemoryUserRepository(UserRepository):
    """
    In-memory implementation of UserRepository.

    Useful for testing and local development without Firestore.
    Data is lost when the application restarts.
    """

    def __init__(self):
        self._users: dict[str, User] = {}

    async def get_by_uid(self, uid: str) -> User | None:
        return self._users.get(uid)

    async def create(self, user: User) -> User:
        if user.uid in self._users:
            raise ValueError(f"User {user.uid} already exists")
        self._users[user.uid] = user
        logger.info(f"Created user: {user.uid}")
        return user

    async def get_or_create(self, uid: str, email: str) -> User:
        if uid in self._users:
            logger.debug(f"Found existing user: {uid}")
            return self._users[uid]

        user = User(uid=uid, email=email)
        self._users[uid] = user
        logger.info(f"Created new user: {uid}")
        return user

    async def save_token(
        self, uid: str, provider: str, token_data: dict[str, Any]
    ) -> OAuthToken:
        # Get user
        user = self._users.get(uid)
        if not user:
            raise ValueError(f"User {uid} not found - cannot save token")

        # Create token from OAuth response
        token = OAuthToken.from_oauth_response(provider, token_data)

        # Update user's tokens
        user.tokens[provider] = token
        user.updated_at = datetime.now(UTC)

        logger.info(f"Saved {provider} token for user {uid}")
        return token

    async def get_token(self, uid: str, provider: str) -> OAuthToken | None:
        user = self._users.get(uid)
        if not user:
            return None
        return user.tokens.get(provider)

    async def delete_token(self, uid: str, provider: str) -> bool:
        user = self._users.get(uid)
        if not user or provider not in user.tokens:
            return False

        del user.tokens[provider]
        user.updated_at = datetime.now(UTC)
        logger.info(f"Deleted {provider} token for user {uid}")
        return True

    async def list_connections(self, uid: str) -> list[str]:
        user = self._users.get(uid)
        if not user:
            return []
        return user.connected_providers()


# Singleton instance for dependency injection
_repository: UserRepository | None = None


def get_user_repository() -> UserRepository:
    """
    Get the user repository singleton.

    Returns FirestoreUserRepository if Firestore is configured
    (GCP_PROJECT_ID and TOKEN_ENCRYPTION_KEY set).
    Falls back to InMemoryUserRepository for testing/development.

    Can be overridden via set_user_repository for testing.
    """
    global _repository
    if _repository is None:
        if _is_firestore_configured():
            try:
                from app.infrastructure.firestore import get_firestore_client
                from app.infrastructure.firestore_repository import (
                    FirestoreUserRepository,
                )

                client = get_firestore_client()
                _repository = FirestoreUserRepository(client)
                logger.info("Using Firestore user repository")
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Firestore, falling back to in-memory: {e}"
                )
                _repository = InMemoryUserRepository()
        else:
            logger.info("Using in-memory user repository")
            _repository = InMemoryUserRepository()
    return _repository


def set_user_repository(repository: UserRepository) -> None:
    """
    Set the user repository implementation.

    Use this to inject Firestore or mock repositories.
    """
    global _repository
    _repository = repository


def reset_user_repository() -> None:
    """
    Reset the user repository singleton.

    Useful for testing to ensure clean state between tests.
    """
    global _repository
    _repository = None
