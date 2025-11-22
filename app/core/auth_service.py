import logging
import os
from urllib.parse import parse_qs, urlparse

from app.infrastructure.firebase_auth import FirebaseAuthAdapter

logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for Magic Link Authentication.

    Handles the business logic of generating links and processing callbacks.
    """

    def __init__(self, auth_adapter: FirebaseAuthAdapter):
        self.auth_adapter = auth_adapter
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")

    async def send_magic_link(self, email: str) -> str:
        """
        Generate a magic link that points directly to this application.

        Args:
            email: The user's email address

        Returns:
            The direct magic link URL
        """
        # We use the callback URL as the continue URL, although we're hijacking the flow
        callback_url = f"{self.base_url}/auth/magic/callback"

        # Generate the standard Firebase link
        # This returns a link to project.firebaseapp.com
        firebase_link = await self.auth_adapter.generate_email_link(email, callback_url)

        # Extract the oobCode from the generated link
        # Link format:
        # https://<project>.firebaseapp.com/__/auth/action?mode=signIn&oobCode=...
        parsed = urlparse(firebase_link)
        query_params = parse_qs(parsed.query)
        oob_code = query_params.get("oobCode", [None])[0]

        if not oob_code:
            logger.error(f"Failed to extract oobCode from link: {firebase_link}")
            raise ValueError("Failed to generate valid magic link")

        # Construct a direct link to our application
        # We include the email to facilitate the REST API exchange
        direct_link = f"{callback_url}?oobCode={oob_code}&email={email}"

        logger.info(f"Generated Magic Link for {email}: {direct_link}")
        return direct_link

    async def handle_callback(self, oob_code: str, email: str) -> str:
        """
        Handle the magic link callback.

        Exchanges the code for a token and creates a session cookie.

        Args:
            oob_code: The one-time code
            email: The user's email

        Returns:
            The session cookie
        """
        # Exchange code for ID token
        id_token = await self.auth_adapter.exchange_code_for_token(email, oob_code)

        # Create session cookie
        session_cookie = await self.auth_adapter.create_session_cookie(id_token)

        return session_cookie

    async def verify_session(self, session_cookie: str) -> dict:
        """
        Verify the session cookie.

        Args:
            session_cookie: The session cookie string

        Returns:
            The decoded claims
        """
        return await self.auth_adapter.verify_session_cookie(session_cookie)
