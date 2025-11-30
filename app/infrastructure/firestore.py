"""
Firestore client configuration and initialization.

This module provides async Firestore client setup that:
- Auto-detects emulator via FIRESTORE_EMULATOR_HOST
- Uses Application Default Credentials in production
"""

import logging
import os
from typing import Optional

from google.cloud.firestore_v1 import AsyncClient

logger = logging.getLogger(__name__)

# Singleton client instance
_firestore_client: Optional[AsyncClient] = None


def get_firestore_client() -> AsyncClient:
    """
    Get the Firestore async client singleton.

    Auto-detects configuration:
    - If FIRESTORE_EMULATOR_HOST is set, connects to emulator
    - Otherwise uses Application Default Credentials

    Returns:
        AsyncClient: Firestore async client instance

    Raises:
        ValueError: If GCP_PROJECT_ID is not set
    """
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client

    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")

    if not project_id:
        raise ValueError(
            "GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT must be set for Firestore"
        )

    # Create client - it will auto-detect emulator from environment
    _firestore_client = AsyncClient(project=project_id)

    if emulator_host:
        logger.info(f"Using Firestore emulator at {emulator_host}")
    else:
        logger.info(f"Firestore client initialized for project: {project_id}")

    return _firestore_client


def is_firestore_available() -> bool:
    """
    Check if Firestore is configured and available.

    Returns:
        True if Firestore can be used, False otherwise
    """
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
    return project_id is not None


async def close_firestore_client() -> None:
    """
    Close the Firestore client connection.

    Should be called during application shutdown.
    """
    global _firestore_client

    if _firestore_client is not None:
        _firestore_client.close()
        _firestore_client = None
        logger.info("Firestore client closed")


def reset_firestore_client() -> None:
    """
    Reset the Firestore client singleton.

    Useful for testing to ensure clean state between tests.
    """
    global _firestore_client
    _firestore_client = None
