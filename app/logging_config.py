"""
Logging configuration for Cloud Run and local environments.

Automatically detects Cloud Run environment and configures appropriate logging:
- Cloud Run: google-cloud-logging with trace correlation
- Local/Test: Standard Python logging to stdout with JSON formatting
"""

import json
import logging
import os
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """
    Custom JSON log formatter.

    Ensures that logs in local development are structured JSON,
    similar to what Google Cloud Logging expects.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON string representing the log record.
        """
        log_object = {
            "timestamp": datetime.now(UTC).isoformat(),
            "severity": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if they exist
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_object.update(record.extra_fields)

        return json.dumps(log_object, default=str)


def setup_global_logging() -> None:
    """
    Configure global logging based on environment.

    When running in Cloud Run (K_SERVICE env var is set):
    - Uses google-cloud-logging for structured logs with trace correlation.
    - Logs appear in Cloud Logging under the jsonPayload field.

    When running locally or in tests:
    - Uses standard Python logging with a custom JSON formatter.
    - Logs are sent to stdout in a structured JSON format.
    """
    is_cloud_run = os.getenv("K_SERVICE") is not None

    if is_cloud_run:
        try:
            import google.cloud.logging

            client = google.cloud.logging.Client()
            client.setup_logging()
            logging.info("Cloud Logging initialized for Cloud Run.")
        except Exception as e:
            # Fallback for Cloud Logging import/initialization errors
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            logging.warning(f"Cloud Logging setup failed, using basic config: {e}")
    else:
        # Local development setup
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)

        # Remove default handlers to avoid duplicate logs
        if len(root_logger.handlers) > 1:
            for h in root_logger.handlers[1:]:
                root_logger.removeHandler(h)
