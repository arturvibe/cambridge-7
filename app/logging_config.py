"""
Logging configuration for Cloud Run and local environments.

Automatically detects Cloud Run environment and configures appropriate logging:
- Cloud Run: google-cloud-logging with trace correlation
- Local/Test: Standard Python logging to stdout
"""

import logging
import os


def setup_global_logging() -> None:
    """
    Configure global logging based on environment.

    This function sets up logging at the module level and should only be called once
    at application startup. Other modules can simply import logging and use
    logging.getLogger(__name__) without importing this module.

    When running in Cloud Run (detected by K_SERVICE env var):
    - Uses google-cloud-logging for structured logs with trace correlation
    - Logs appear in Cloud Logging with jsonPayload field
    - Automatic correlation with HTTP request traces

    When running locally or in tests:
    - Uses standard Python logging to stdout
    - Simple text format for development
    """
    # Check if running in Cloud Run
    # Cloud Run sets K_SERVICE environment variable
    is_cloud_run = os.getenv("K_SERVICE") is not None

    if is_cloud_run:
        try:
            # Import and setup Cloud Logging
            import google.cloud.logging

            client = google.cloud.logging.Client()
            client.setup_logging()
            logging.info("Cloud Logging initialized for Cloud Run")
        except Exception as e:
            # Fallback if Cloud Logging setup fails
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logging.warning(
                f"Failed to initialize Cloud Logging, using stdout: {str(e)}"
            )
    else:
        # Local development or testing - use stdout
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
