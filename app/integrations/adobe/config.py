"""
Frame.io API configuration.

Contains constants and configuration for interacting with Frame.io API v2.
"""

from dataclasses import dataclass
from functools import lru_cache
import os


# Frame.io API base URL
FRAMEIO_BASE_URL = "https://api.frame.io/v2"

# Adobe IMS token refresh endpoint
ADOBE_TOKEN_REFRESH_URL = "https://ims-na1.adobelogin.com/ims/token/v3"


@dataclass
class FrameioConfig:
    """Configuration for Frame.io API access."""

    base_url: str = FRAMEIO_BASE_URL
    token_refresh_url: str = ADOBE_TOKEN_REFRESH_URL
    adobe_client_id: str | None = None
    adobe_client_secret: str | None = None

    @classmethod
    def from_env(cls) -> "FrameioConfig":
        """Load configuration from environment variables."""
        return cls(
            adobe_client_id=os.getenv("ADOBE_CLIENT_ID"),
            adobe_client_secret=os.getenv("ADOBE_CLIENT_SECRET"),
        )

    def can_refresh_tokens(self) -> bool:
        """Check if token refresh is possible (credentials available)."""
        return bool(self.adobe_client_id and self.adobe_client_secret)


@lru_cache()
def get_frameio_config() -> FrameioConfig:
    """Get Frame.io configuration singleton."""
    return FrameioConfig.from_env()
