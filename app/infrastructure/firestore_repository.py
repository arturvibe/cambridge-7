"""
Firestore implementation of UserRepository.

Stores users and OAuth tokens in Firestore with encrypted token storage.
This is a driven adapter that implements the UserRepository interface.
"""

import logging
from datetime import datetime, UTC
from typing import Any

from google.cloud.firestore_v1 import AsyncClient

from app.infrastructure.encryption import (
    decrypt_token_optional,
    encrypt_token_optional,
)
from app.users.models import OAuthToken, User

logger = logging.getLogger(__name__)


class FirestoreUserRepository:
    """
    Firestore implementation of UserRepository.

    Data model:
    - Collection: users
      - Document ID: {firebase_uid}
      - Fields: uid, email, created_at, updated_at
      - Subcollection: tokens
        - Document ID: {provider}
        - Fields: provider, access_token (encrypted), refresh_token (encrypted),
                  expires_at, token_type, scope, connected_at
    """

    def __init__(self, db: AsyncClient):
        """
        Initialize Firestore repository.

        Args:
            db: Firestore async client instance
        """
        self._db = db
        self._users = db.collection("users")

    async def get_by_uid(self, uid: str) -> User | None:
        """
        Get a user by Firebase UID.

        Args:
            uid: Firebase user ID

        Returns:
            User if found, None otherwise
        """
        doc_ref = self._users.document(uid)
        doc = await doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        if data is None:
            return None

        # Load tokens from subcollection
        tokens = await self._load_tokens(uid)

        return User(
            uid=data["uid"],
            email=data["email"],
            tokens=tokens,
            created_at=data.get("created_at", datetime.now(UTC)),
            updated_at=data.get("updated_at", datetime.now(UTC)),
        )

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
        doc_ref = self._users.document(user.uid)
        doc = await doc_ref.get()

        if doc.exists:
            raise ValueError(f"User {user.uid} already exists")

        # Store user document
        await doc_ref.set(
            {
                "uid": user.uid,
                "email": user.email,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
        )

        logger.info(f"Created user: {user.uid}")
        return user

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
        existing = await self.get_by_uid(uid)
        if existing:
            logger.debug(f"Found existing user: {uid}")
            return existing

        user = User(uid=uid, email=email)
        await self.create(user)
        logger.info(f"Created new user: {uid}")
        return user

    async def save_token(
        self, uid: str, provider: str, token_data: dict[str, Any]
    ) -> OAuthToken:
        """
        Save OAuth token for a user.

        Tokens are encrypted before storage.

        Args:
            uid: Firebase user ID
            provider: OAuth provider name (google, adobe)
            token_data: Raw token dict from authlib

        Returns:
            Saved OAuthToken

        Raises:
            ValueError: If user does not exist
        """
        # Ensure user exists
        user_doc = self._users.document(uid)
        user_snapshot = await user_doc.get()

        if not user_snapshot.exists:
            raise ValueError(f"User {uid} not found - cannot save token")

        # Create token from OAuth response
        token = OAuthToken.from_oauth_response(provider, token_data)

        # Encrypt sensitive fields
        encrypted_access_token = encrypt_token_optional(token.access_token)
        encrypted_refresh_token = encrypt_token_optional(token.refresh_token)

        # Store token in subcollection
        token_doc = user_doc.collection("tokens").document(provider)
        await token_doc.set(
            {
                "provider": token.provider,
                "access_token": encrypted_access_token,
                "refresh_token": encrypted_refresh_token,
                "expires_at": token.expires_at,
                "token_type": token.token_type,
                "scope": token.scope,
                "connected_at": token.connected_at,
            }
        )

        # Update user's updated_at timestamp
        await user_doc.update({"updated_at": datetime.now(UTC)})

        logger.info(f"Saved {provider} token for user {uid}")
        return token

    async def get_token(self, uid: str, provider: str) -> OAuthToken | None:
        """
        Get OAuth token for a specific provider.

        Tokens are decrypted before returning.

        Args:
            uid: Firebase user ID
            provider: OAuth provider name

        Returns:
            OAuthToken if found, None otherwise
        """
        token_doc = self._users.document(uid).collection("tokens").document(provider)
        doc = await token_doc.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        if data is None:
            return None

        # Decrypt sensitive fields
        access_token = decrypt_token_optional(data.get("access_token"))
        refresh_token = decrypt_token_optional(data.get("refresh_token"))

        if access_token is None:
            logger.error(f"Failed to decrypt access token for {uid}/{provider}")
            return None

        return OAuthToken(
            provider=data["provider"],
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=data.get("expires_at"),
            token_type=data.get("token_type", "Bearer"),
            scope=data.get("scope"),
            connected_at=data.get("connected_at", datetime.now(UTC)),
        )

    async def delete_token(self, uid: str, provider: str) -> bool:
        """
        Delete OAuth token (disconnect service).

        Args:
            uid: Firebase user ID
            provider: OAuth provider name

        Returns:
            True if deleted, False if not found
        """
        # Check if user exists
        user_doc = self._users.document(uid)
        user_snapshot = await user_doc.get()

        if not user_snapshot.exists:
            return False

        # Check if token exists
        token_doc = user_doc.collection("tokens").document(provider)
        token_snapshot = await token_doc.get()

        if not token_snapshot.exists:
            return False

        # Delete the token document
        await token_doc.delete()

        # Update user's updated_at timestamp
        await user_doc.update({"updated_at": datetime.now(UTC)})

        logger.info(f"Deleted {provider} token for user {uid}")
        return True

    async def list_connections(self, uid: str) -> list[str]:
        """
        List connected OAuth providers for a user.

        Args:
            uid: Firebase user ID

        Returns:
            List of provider names
        """
        # Check if user exists
        user_doc = self._users.document(uid)
        user_snapshot = await user_doc.get()

        if not user_snapshot.exists:
            return []

        # Get all tokens in subcollection
        tokens_ref = user_doc.collection("tokens")
        docs = tokens_ref.stream()

        providers = []
        async for doc in docs:
            providers.append(doc.id)

        return providers

    async def _load_tokens(self, uid: str) -> dict[str, OAuthToken]:
        """
        Load all tokens for a user from the tokens subcollection.

        Args:
            uid: Firebase user ID

        Returns:
            Dictionary of provider -> OAuthToken
        """
        tokens: dict[str, OAuthToken] = {}
        tokens_ref = self._users.document(uid).collection("tokens")
        docs = tokens_ref.stream()

        async for doc in docs:
            data = doc.to_dict()
            if data is None:
                continue

            # Decrypt sensitive fields
            access_token = decrypt_token_optional(data.get("access_token"))
            refresh_token = decrypt_token_optional(data.get("refresh_token"))

            if access_token is None:
                logger.error(f"Failed to decrypt access token for {uid}/{doc.id}")
                continue

            token = OAuthToken(
                provider=data["provider"],
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=data.get("expires_at"),
                token_type=data.get("token_type", "Bearer"),
                scope=data.get("scope"),
                connected_at=data.get("connected_at", datetime.now(UTC)),
            )
            tokens[doc.id] = token

        return tokens
