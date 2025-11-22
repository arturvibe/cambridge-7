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
    """Configuration for authentication module."""

    def __init__(self):
        self.firebase_web_api_key = os.getenv("FIREBASE_WEB_API_KEY", "")
        self.base_url = os.getenv("BASE_URL", "http://localhost:8080")
        self.session_cookie_name = "session"
        # Session cookie expiration: 14 days (in seconds)
        self.session_cookie_max_age = 60 * 60 * 24 * 14

    @property
    def callback_url(self) -> str:
        """URL for the magic link callback endpoint."""
        return f"{self.base_url}/auth/magic/callback"

    def validate(self) -> None:
        """Validate required configuration."""
        if not self.firebase_web_api_key:
            raise ValueError(
                "FIREBASE_WEB_API_KEY environment variable is required"
            )
        if not self.base_url:
            raise ValueError("BASE_URL environment variable is required")


@lru_cache()
def get_auth_config() -> AuthConfig:
    """Get authentication configuration (singleton)."""
    return AuthConfig()


def initialize_firebase() -> None:
    """
    Initialize Firebase Admin SDK.

    Uses Application Default Credentials (ADC) which works with:
    - Local dev: `gcloud auth application-default login`
    - Cloud Run: Service account automatically attached
    - GOOGLE_APPLICATION_CREDENTIALS env var
    """
    if firebase_admin._apps:
        logger.debug("Firebase Admin SDK already initialized")
        return

    try:
        # Initialize with default credentials
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        raise


def get_firebase_auth():
    """Get Firebase Auth module (ensures initialization)."""
    initialize_firebase()
    return firebase_auth
