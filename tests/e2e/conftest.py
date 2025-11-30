"""
Shared test configuration for E2E tests.

Sets up environment variables required for E2E testing with emulators.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_environment():
    """Set up environment variables for E2E tests."""
    # Set BASE_URL for magic link service
    os.environ.setdefault("BASE_URL", "http://localhost:8080")
    # Set Firebase emulator host if not already set
    os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "localhost:9099")
    # Set Firestore emulator host
    os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "localhost:8086")
    # Set Firebase API key for emulator
    os.environ.setdefault("FIREBASE_WEB_API_KEY", "fake-api-key")
    # Set GCP project ID
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "cambridge-local")
    os.environ.setdefault("GCP_PROJECT_ID", "cambridge-local")
    # Set test encryption key
    os.environ.setdefault(
        "TOKEN_ENCRYPTION_KEY", "3xpo7t61pLEqmOiHEZs4qIvrPjieKmO1Pg5OSdwDRAI="
    )
    # Set session secret
    os.environ.setdefault("SESSION_SECRET_KEY", "test-secret")
    yield
