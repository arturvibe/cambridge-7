"""
Shared test configuration for E2E tests.

Sets up environment variables required for E2E testing with Firebase emulator.
"""

import os
import socket

import pytest


def is_emulator_available(host: str = "localhost", port: int = 9099) -> bool:
    """Check if Firebase emulator is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_environment():
    """Set up environment variables for E2E tests."""
    # Set BASE_URL for magic link service
    os.environ.setdefault("BASE_URL", "http://localhost:8080")
    # Set Firebase emulator host if not already set
    os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
    # Set Firebase API key for emulator
    os.environ.setdefault("FIREBASE_WEB_API_KEY", "fake-api-key")
    # Set GCP project ID for Firebase
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "cambridge-local")
    os.environ.setdefault("GCP_PROJECT_ID", "cambridge-local")
    yield


@pytest.fixture(autouse=True)
def skip_without_emulator():
    """Skip E2E tests if Firebase emulator is not available."""
    if not is_emulator_available():
        pytest.skip("Firebase Auth emulator not available at localhost:9099")
