"""
Authentication services for magic link flow.

Contains business logic for generating magic links, exchanging tokens,
and creating session cookies.
"""

import logging
from typing import Any

import httpx
from firebase_admin import auth as firebase_auth

from app.auth.config import get_auth_config, get_firebase_auth


logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class MagicLinkService:
    """Service for generating and handling magic links."""

    def __init__(self):
        self.config = get_auth_config()
        self._firebase_auth = get_firebase_auth()

    def generate_magic_link(self, email: str) -> str:
        """
        Generate a magic link for the given email.

        Args:
            email: User's email address

        Returns:
            Complete magic link URL

        Raises:
            AuthenticationError: If link generation fails
        """
        try:
            # Include email in callback URL since Firebase doesn't add it
            from urllib.parse import urlencode

            callback_with_email = f"{self.config.callback_url}?{urlencode({'email': email})}"

            # Configure the action code settings
            action_code_settings = firebase_auth.ActionCodeSettings(
                url=callback_with_email,
                handle_code_in_app=False,
            )

            # Generate the email sign-in link
            link = self._firebase_auth.generate_sign_in_with_email_link(
                email=email,
                action_code_settings=action_code_settings,
            )

            logger.info(
                f"Generated magic link for email: {email}",
                extra={"email": email},
            )

            return str(link)

        except Exception as e:
            logger.error(f"Failed to generate magic link: {e}")
            raise AuthenticationError(f"Failed to generate magic link: {e}")


class TokenExchangeService:
    """Service for exchanging oobCode for Firebase tokens."""

    # Firebase Auth REST API endpoint for email link sign-in
    FIREBASE_SIGNIN_URL = (
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink"
    )

    def __init__(self):
        self.config = get_auth_config()

    async def exchange_oob_code_for_id_token(self, oob_code: str, email: str) -> str:
        """
        Exchange oobCode for a Firebase ID token using REST API.

        Args:
            oob_code: The one-time out-of-band code from the magic link
            email: The user's email address

        Returns:
            Firebase ID token

        Raises:
            AuthenticationError: If token exchange fails
        """
        url = f"{self.FIREBASE_SIGNIN_URL}?key={self.config.firebase_web_api_key}"

        payload = {
            "oobCode": oob_code,
            "email": email,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)

                if response.status_code != 200:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get(
                        "message", "Unknown error"
                    )
                    logger.error(
                        f"Firebase sign-in failed: {error_message}",
                        extra={"status_code": response.status_code},
                    )
                    raise AuthenticationError(
                        f"Firebase sign-in failed: {error_message}"
                    )

                data = response.json()
                id_token = data.get("idToken")

                if not id_token:
                    raise AuthenticationError("No ID token in response")

                logger.info(
                    "Successfully exchanged oobCode for ID token",
                    extra={"email": email},
                )

                return str(id_token)

        except httpx.RequestError as e:
            logger.error(f"Network error during token exchange: {e}")
            raise AuthenticationError(f"Network error: {e}")


class SessionCookieService:
    """Service for creating and verifying session cookies."""

    def __init__(self):
        self.config = get_auth_config()
        self._firebase_auth = get_firebase_auth()

    def create_session_cookie(self, id_token: str) -> str:
        """
        Create a session cookie from an ID token.

        Args:
            id_token: Firebase ID token

        Returns:
            Session cookie string

        Raises:
            AuthenticationError: If cookie creation fails
        """
        try:
            # Create session cookie (expires in 14 days)
            session_cookie = self._firebase_auth.create_session_cookie(
                id_token=id_token,
                expires_in=self.config.session_cookie_max_age,
            )

            logger.info("Successfully created session cookie")
            return str(session_cookie)

        except firebase_auth.InvalidIdTokenError:
            logger.error("Invalid ID token provided for session cookie")
            raise AuthenticationError("Invalid ID token")
        except firebase_auth.ExpiredIdTokenError:
            logger.error("Expired ID token provided for session cookie")
            raise AuthenticationError("Expired ID token")
        except Exception as e:
            logger.error(f"Failed to create session cookie: {e}")
            raise AuthenticationError(f"Failed to create session cookie: {e}")

    def verify_session_cookie(
        self, session_cookie: str, check_revoked: bool = True
    ) -> dict[str, Any]:
        """
        Verify a session cookie and return decoded claims.

        Args:
            session_cookie: The session cookie string
            check_revoked: Whether to check if the token has been revoked

        Returns:
            Decoded token claims (includes uid, email, etc.)

        Raises:
            AuthenticationError: If verification fails
        """
        try:
            decoded_claims = self._firebase_auth.verify_session_cookie(
                session_cookie=session_cookie,
                check_revoked=check_revoked,
            )

            logger.debug(
                f"Session cookie verified for user: {decoded_claims.get('uid')}"
            )
            return dict(decoded_claims)

        except firebase_auth.InvalidSessionCookieError:
            logger.warning("Invalid session cookie")
            raise AuthenticationError("Invalid session cookie")
        except firebase_auth.ExpiredSessionCookieError:
            logger.warning("Expired session cookie")
            raise AuthenticationError("Expired session cookie")
        except firebase_auth.RevokedSessionCookieError:
            logger.warning("Revoked session cookie")
            raise AuthenticationError("Revoked session cookie")
        except Exception as e:
            logger.error(f"Failed to verify session cookie: {e}")
            raise AuthenticationError(f"Session verification failed: {e}")
