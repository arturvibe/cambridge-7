"""
Firebase configuration and initialization.

Handles Firebase Admin SDK initialization and environment configuration.
"""

import os
import logging
from functools import lru_cache

import firebase_admin
from firebase_admin import auth as firebase_auth


logger = logging.getLogger(__name__)


class AuthConfig:
    """Configuration for authentication module.

    Required environment variables:
    - FIREBASE_WEB_API_KEY: Required in production (skip if using emulator)
    - BASE_URL: Required always

    Optional:
    - FIREBASE_AUTH_EMULATOR_HOST: Set for local development with emulator
    """

    def __init__(self):
        self.firebase_web_api_key = os.getenv("FIREBASE_WEB_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.firebase_auth_emulator_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
        self.session_cookie_name = "session"
        # Session cookie expiration: 14 days (in seconds)
        self.session_cookie_max_age = 60 * 60 * 24 * 14

    @property
    def callback_url(self) -> str:
        """URL for the magic link callback endpoint."""
        return f"{self.base_url}/auth/magic/callback"

    @property
    def using_emulator(self) -> bool:
        """Check if using Firebase Auth Emulator."""
        return bool(self.firebase_auth_emulator_host)

    def validate(self) -> None:
        """Validate required configuration. Call at startup to fail fast."""
        if not self.base_url:
            raise ValueError("BASE_URL environment variable is required")
        # Skip API key validation when using emulator
        if not self.using_emulator and not self.firebase_web_api_key:
            raise ValueError("FIREBASE_WEB_API_KEY environment variable is required")


@lru_cache()
def get_auth_config() -> AuthConfig:
    """Get authentication configuration (singleton)."""
    return AuthConfig()


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK.

    Auto-detects Firebase Auth Emulator via FIREBASE_AUTH_EMULATOR_HOST.
    Uses Application Default Credentials (ADC) for production.
    """
    if firebase_admin._apps:
        logger.debug("Firebase Admin SDK already initialized")
        return

    emulator_host = os.getenv("FIREBASE_AUTH_EMULATOR_HOST")
    if emulator_host:
        logger.info(f"Using Firebase Auth Emulator at {emulator_host}")

    try:
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise


def get_firebase_auth():
    """Get Firebase Auth module (ensures initialization)."""
    initialize_firebase()
    return firebase_auth
