import logging
import os
from typing import Any, Dict, cast

import firebase_admin
import httpx
from firebase_admin import auth
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)


class FirebaseAuthAdapter:
    """
    Adapter for Firebase Authentication.

    Handles interactions with Firebase Admin SDK and Firebase Auth REST API.
    """

    def __init__(self) -> None:
        """Initialize the adapter and Firebase Admin SDK."""
        self.api_key = os.getenv("FIREBASE_WEB_API_KEY")
        if not self.api_key:
            logger.warning("FIREBASE_WEB_API_KEY not set. Auth exchange will fail.")

        # Initialize Firebase Admin SDK if not already initialized
        try:
            firebase_admin.get_app()
        except ValueError:
            # Initialize with default credentials (Cloud Run identity or local ADC)
            try:
                # explicit credential loading for strict environments,
                # but initialize_app() usually handles ADC automatically.
                # We just call initialize_app() to let it find credentials.
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
                raise

    async def generate_email_link(self, email: str, redirect_url: str) -> str:
        """
        Generate a magic link for the given email.

        Args:
            email: User's email address
            redirect_url: URL to continue to after verification

        Returns:
            The generated magic link
        """

        def _generate() -> str:
            action_code_settings = auth.ActionCodeSettings(
                url=redirect_url,
                handle_code_in_app=True,
            )
            link = auth.generate_sign_in_with_email_link(email, action_code_settings)
            return cast(str, link)

        result = await run_in_threadpool(_generate)
        return cast(str, result)

    async def exchange_code_for_token(self, email: str, oob_code: str) -> str:
        """
        Exchange oobCode for an ID Token using Firebase Auth REST API.

        Args:
            email: User's email
            oob_code: The one-time code from the magic link

        Returns:
            Firebase ID Token
        """
        if not self.api_key:
            raise ValueError("FIREBASE_WEB_API_KEY is required for token exchange")

        url = (
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink"
            f"?key={self.api_key}"
        )
        payload = {"email": email, "oobCode": oob_code}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                logger.error(f"Firebase REST API error: {response.text}")
                raise ValueError(f"Failed to sign in: {response.text}")

            data = response.json()
            return cast(str, data["idToken"])

    async def create_session_cookie(
        self, id_token: str, expires_in: int = 60 * 60 * 24 * 5
    ) -> str:
        """
        Create a session cookie from an ID token.

        Args:
            id_token: Firebase ID token
            expires_in: Expiration time in seconds (default 5 days)

        Returns:
            Session cookie string
        """

        def _create() -> str:
            cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
            return cast(str, cookie)

        result = await run_in_threadpool(_create)
        return cast(str, result)

    async def verify_session_cookie(self, session_cookie: str) -> Dict[str, Any]:
        """
        Verify a session cookie.

        Args:
            session_cookie: The session cookie to verify

        Returns:
            Decoded claims dictionary

        Raises:
            ValueError: If cookie is invalid or revoked
        """

        def _verify() -> Dict[str, Any]:
            claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
            return cast(Dict[str, Any], claims)

        result = await run_in_threadpool(_verify)
        return cast(Dict[str, Any], result)
